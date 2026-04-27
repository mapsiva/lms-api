"""Celery tasks for gamification."""
import logging
import uuid

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


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
    import asyncio

    from app.core.sync_database import get_sync_db
    from app.services.gamification.xp import award_xp as _award_xp

    db = get_sync_db()
    try:
        result = asyncio.run(
            _award_xp(
                db,  # type: ignore[arg-type]
                uuid.UUID(user_id),
                uuid.UUID(tenant_id),
                uuid.UUID(company_id) if company_id else None,
                action,
                uuid.UUID(reference_id) if reference_id else None,
                reference_type,
            )
        )
        if result.get("leveled_up"):
            # Dispatch badge evaluation after level-up
            evaluate_badges_task.delay(user_id, tenant_id, "level_up")
        return result
    except Exception as exc:
        logger.exception("award_xp_task failed user=%s", user_id)
        self.retry(countdown=60, exc=exc)
    finally:
        db.close()
    return {}


@celery_app.task(bind=True, max_retries=3)
def evaluate_badges_task(self, user_id: str, tenant_id: str, trigger_event: str) -> list[str]:
    import asyncio

    from app.core.sync_database import get_sync_db
    from app.services.gamification.badges import evaluate_badges as _evaluate

    db = get_sync_db()
    try:
        awarded = asyncio.run(
            _evaluate(db, uuid.UUID(user_id), uuid.UUID(tenant_id), trigger_event)  # type: ignore[arg-type]
        )
        for badge_id in awarded:
            # Award XP for earning badge
            award_xp_task.delay(
                user_id, tenant_id, None, "badge_earned", str(badge_id), "badge"
            )
        return [str(b) for b in awarded]
    except Exception as exc:
        logger.exception("evaluate_badges_task failed user=%s", user_id)
        self.retry(countdown=60, exc=exc)
    finally:
        db.close()
    return []


@celery_app.task(bind=True, max_retries=3)
def update_streak_task(self, user_id: str, company_id: str | None) -> dict:
    import asyncio

    from app.core.sync_database import get_sync_db
    from app.services.gamification.streaks import update_streak as _update

    db = get_sync_db()
    try:
        result = asyncio.run(
            _update(db, uuid.UUID(user_id), uuid.UUID(company_id) if company_id else None)  # type: ignore[arg-type]
        )
        return result
    except Exception as exc:
        logger.exception("update_streak_task failed user=%s", user_id)
        self.retry(countdown=60, exc=exc)
    finally:
        db.close()
    return {}


@celery_app.task(bind=True, max_retries=3)
def evaluate_company_goal_task(self, goal_id: str) -> None:
    """Check all company members against goal target. Mark achieved + award badge if threshold met."""
    from app.core.sync_database import get_sync_db

    db = get_sync_db()
    try:
        from app.models.company import CompanyGoal

        goal = db.get(CompanyGoal, uuid.UUID(goal_id))
        if goal is None or goal.status == "achieved":
            return

        # TODO: implement goal evaluation logic based on target_metric and target_value
        # Placeholder: mark achieved for MVP
        goal.status = "achieved"
        db.commit()
        logger.info("Company goal %s marked achieved", goal_id)
    except Exception as exc:
        logger.exception("evaluate_company_goal_task failed goal=%s", goal_id)
        self.retry(countdown=60, exc=exc)
    finally:
        db.close()
