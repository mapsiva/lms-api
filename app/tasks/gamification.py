"""Celery tasks for gamification."""
import asyncio
import logging
import uuid

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _async_session():
    from app.core.database import AsyncSessionLocal

    if AsyncSessionLocal is None:
        raise RuntimeError("Async DB not initialised in worker — check worker_init signal")
    return AsyncSessionLocal()


@celery_app.task(bind=True, max_retries=3)
def award_xp_task(
    self,
    user_id: str,
    tenant_id: str,
    company_id: str | None,
    action: str,
    reference_id: str | None = None,
    reference_type: str | None = None,
) -> dict:
    from app.services.gamification.xp import award_xp as _award_xp

    async def _run() -> dict:
        async with _async_session() as session:
            return await _award_xp(
                session,
                uuid.UUID(user_id),
                uuid.UUID(tenant_id),
                uuid.UUID(company_id) if company_id else None,
                action,
                uuid.UUID(reference_id) if reference_id else None,
                reference_type,
            )

    try:
        result = asyncio.run(_run())
        if result.get("leveled_up"):
            evaluate_badges_task.delay(user_id, tenant_id, "level_up")
        return result
    except Exception as exc:
        logger.exception("award_xp_task failed user=%s", user_id)
        self.retry(countdown=60, exc=exc)
    return {}


@celery_app.task(bind=True, max_retries=3)
def evaluate_badges_task(self, user_id: str, tenant_id: str, trigger_event: str) -> list[str]:
    from app.services.gamification.badges import evaluate_badges as _evaluate

    async def _run() -> list[uuid.UUID]:
        async with _async_session() as session:
            return await _evaluate(
                session, uuid.UUID(user_id), uuid.UUID(tenant_id), trigger_event
            )

    try:
        awarded = asyncio.run(_run())
        for badge_id in awarded:
            award_xp_task.delay(user_id, tenant_id, None, "badge_earned", str(badge_id), "badge")
        return [str(b) for b in awarded]
    except Exception as exc:
        logger.exception("evaluate_badges_task failed user=%s", user_id)
        self.retry(countdown=60, exc=exc)
    return []


@celery_app.task(bind=True, max_retries=3)
def update_streak_task(self, user_id: str, company_id: str | None) -> dict:
    from app.services.gamification.streaks import update_streak as _update

    async def _run() -> dict:
        async with _async_session() as session:
            return await _update(
                session,
                uuid.UUID(user_id),
                uuid.UUID(company_id) if company_id else None,
            )

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("update_streak_task failed user=%s", user_id)
        self.retry(countdown=60, exc=exc)
    return {}


@celery_app.task(bind=True, max_retries=3)
def evaluate_company_goal_task(self, goal_id: str) -> None:
    """Evaluate company goal metric against target. Mark achieved + dispatch badge reward if met."""
    from app.core.sync_database import get_sync_db

    db = get_sync_db()
    try:
        from sqlalchemy import func, select

        from app.models.company import CompanyGoal
        from app.models.enrollment import Enrollment
        from app.models.gamification import XPEvent
        from app.models.progress import LessonProgress
        from app.models.quiz import QuizBattleAnswer
        from app.models.user import User

        goal = db.get(CompanyGoal, uuid.UUID(goal_id))
        if goal is None or goal.status == "achieved":
            return

        company_id = goal.company_id
        metric = goal.target_metric
        target = float(goal.target_value)
        current_value: float = 0.0

        if metric == "total_xp":
            row = db.execute(
                select(func.sum(XPEvent.amount)).where(XPEvent.company_id == company_id)
            ).scalar()
            current_value = float(row or 0)

        elif metric == "enrollments":
            row = db.execute(
                select(func.count(Enrollment.id)).where(Enrollment.company_id == company_id)
            ).scalar()
            current_value = float(row or 0)

        elif metric == "completion_rate":
            enrolled = db.execute(
                select(func.count(func.distinct(User.id))).where(User.company_id == company_id)
            ).scalar() or 0
            if enrolled == 0:
                return
            completed = db.execute(
                select(func.count(func.distinct(LessonProgress.user_id)))
                .join(User, User.id == LessonProgress.user_id)
                .where(
                    User.company_id == company_id,
                    LessonProgress.completed_at.isnot(None),
                )
            ).scalar() or 0
            current_value = (completed / enrolled) * 100

        elif metric == "avg_score":
            row = db.execute(
                select(func.avg(QuizBattleAnswer.score))
                .join(User, User.id == QuizBattleAnswer.user_id)
                .where(User.company_id == company_id)
            ).scalar()
            current_value = float(row or 0)

        if current_value >= target:
            goal.status = "achieved"
            db.commit()
            logger.info(
                "Company goal %s achieved (metric=%s value=%.2f)", goal_id, metric, current_value
            )
            if goal.badge_reward_id:
                users = db.execute(
                    select(User.id).where(User.company_id == company_id)
                ).scalars().all()
                for user_id in users:
                    evaluate_badges_task.delay(str(user_id), str(goal.company_id), "goal_achieved")
        else:
            logger.debug(
                "Company goal %s not yet achieved (metric=%s current=%.2f target=%.2f)",
                goal_id,
                metric,
                current_value,
                target,
            )
    except Exception as exc:
        logger.exception("evaluate_company_goal_task failed goal=%s", goal_id)
        self.retry(countdown=60, exc=exc)
    finally:
        db.close()
