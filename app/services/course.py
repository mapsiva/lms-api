import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.integrations.video.bunny import BunnyVideoProvider
from app.models.course import Course, Lesson, Module
from app.models.enrollment import Enrollment
from app.models.product import ProductCourse
from app.models.progress import LessonProgress
from app.schemas.course import (
    ContinueResponse,
    CourseDetail,
    LessonDetailResponse,
    LessonSummary,
    ModuleWithLessons,
    ProgressUpdate,
    SearchResult,
)

VIDEO_URL_TTL = 7200  # 2 hours


async def _get_active_enrollment_product_ids(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> list[uuid.UUID]:
    result = await db.execute(
        select(Enrollment.product_id).where(
            Enrollment.tenant_id == tenant_id,
            Enrollment.user_id == user_id,
            Enrollment.status == "active",
        )
    )
    return list(result.scalars().all())


async def _is_user_enrolled_in_course(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, course_id: uuid.UUID
) -> tuple[bool, Optional[Enrollment]]:
    product_ids = await _get_active_enrollment_product_ids(db, tenant_id, user_id)
    if not product_ids:
        return False, None
    result = await db.execute(
        select(ProductCourse.product_id).where(
            ProductCourse.course_id == course_id,
            ProductCourse.product_id.in_(product_ids),
        ).limit(1)
    )
    product_id = result.scalar_one_or_none()
    if not product_id:
        return False, None
    enrollment_result = await db.execute(
        select(Enrollment).where(
            Enrollment.tenant_id == tenant_id,
            Enrollment.user_id == user_id,
            Enrollment.product_id == product_id,
            Enrollment.status == "active",
        )
    )
    return True, enrollment_result.scalar_one_or_none()


def _check_drip(lesson: Lesson, enrollment: Enrollment) -> tuple[bool, str]:
    if lesson.drip_type == "immediate":
        return True, "accessible"

    now = datetime.now(timezone.utc)

    if lesson.drip_type == "fixed_date":
        drip_value = lesson.drip_value or {}
        date_str = drip_value.get("date")
        if not date_str:
            return True, "accessible"
        unlock_date = datetime.fromisoformat(date_str)
        if unlock_date.tzinfo is None:
            unlock_date = unlock_date.replace(tzinfo=timezone.utc)
        if now >= unlock_date:
            return True, "accessible"
        return False, f"unlocks on {date_str}"

    if lesson.drip_type == "days_after_enrollment":
        drip_value = lesson.drip_value or {}
        days = int(drip_value.get("days", 0))
        enrolled_at = enrollment.created_at
        if enrolled_at.tzinfo is None:
            enrolled_at = enrolled_at.replace(tzinfo=timezone.utc)
        if now >= enrolled_at + timedelta(days=days):
            return True, "accessible"
        return False, f"unlocks {days} days after enrollment"

    return True, "accessible"


async def list_enrolled_courses(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> list[Course]:
    product_ids = await _get_active_enrollment_product_ids(db, tenant_id, user_id)
    if not product_ids:
        return []
    course_ids_result = await db.execute(
        select(ProductCourse.course_id).where(ProductCourse.product_id.in_(product_ids))
    )
    course_ids = list(course_ids_result.scalars().all())
    if not course_ids:
        return []
    result = await db.execute(
        select(Course).where(
            Course.tenant_id == tenant_id,
            Course.id.in_(course_ids),
            Course.status == "published",
        ).order_by(Course.title)
    )
    return list(result.scalars().all())


async def get_course_detail(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, slug: str
) -> CourseDetail:
    result = await db.execute(
        select(Course).where(Course.tenant_id == tenant_id, Course.slug == slug)
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise AppError(ErrorCode.COURSE_NOT_FOUND)

    enrolled, _ = await _is_user_enrolled_in_course(db, tenant_id, user_id, course.id)
    if not enrolled and not course.is_free:
        raise AppError(ErrorCode.NOT_ENROLLED)

    modules_result = await db.execute(
        select(Module)
        .where(Module.course_id == course.id, Module.tenant_id == tenant_id, Module.is_hidden.is_(False))
        .order_by(Module.order_index)
    )
    modules = modules_result.scalars().all()

    module_list = []
    for mod in modules:
        lessons_result = await db.execute(
            select(Lesson)
            .where(Lesson.module_id == mod.id, Lesson.tenant_id == tenant_id, Lesson.is_hidden.is_(False))
            .order_by(Lesson.order_index)
        )
        lessons = lessons_result.scalars().all()
        module_list.append(
            ModuleWithLessons(
                id=mod.id,
                title=mod.title,
                order_index=mod.order_index,
                is_hidden=mod.is_hidden,
                lessons=[LessonSummary.model_validate(lesson) for lesson in lessons],
            )
        )

    return CourseDetail(
        id=course.id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        thumbnail_url=course.thumbnail_url,
        status=course.status,
        certificate_enabled=course.certificate_enabled,
        modules=module_list,
    )


async def get_lesson_detail(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    lesson_id: uuid.UUID,
    bunny_provider: type[BunnyVideoProvider] = BunnyVideoProvider,
) -> LessonDetailResponse:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant_id:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)

    module = await db.get(Module, lesson.module_id)
    if module is None:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)

    enrolled, enrollment = await _is_user_enrolled_in_course(
        db, tenant_id, user_id, module.course_id
    )
    if not enrolled and not lesson.is_free_preview:
        raise AppError(ErrorCode.NOT_ENROLLED)

    drip_accessible, drip_reason = True, "accessible"
    if enrolled and enrollment:
        drip_accessible, drip_reason = _check_drip(lesson, enrollment)

    # Prerequisite drip: check previous lesson progress
    if lesson.drip_type == "prerequisite" and lesson.drip_value:
        prereq_lesson_id = lesson.drip_value.get("lesson_id")
        if prereq_lesson_id:
            progress_result = await db.execute(
                select(LessonProgress).where(
                    LessonProgress.user_id == user_id,
                    LessonProgress.lesson_id == uuid.UUID(prereq_lesson_id),
                    LessonProgress.completed_at.isnot(None),
                )
            )
            if progress_result.scalar_one_or_none() is None:
                drip_accessible = False
                drip_reason = "prerequisite lesson not completed"

    playback_url = None
    if lesson.video_provider == "bunny" and lesson.video_external_id and drip_accessible:
        bunny = bunny_provider()
        playback_url = await bunny.get_playback_url(lesson.video_external_id, VIDEO_URL_TTL)

    return LessonDetailResponse(
        id=lesson.id,
        title=lesson.title,
        lesson_type=lesson.lesson_type,
        order_index=lesson.order_index,
        duration_seconds=lesson.duration_seconds,
        is_free_preview=lesson.is_free_preview,
        video_provider=lesson.video_provider,
        video_external_id=lesson.video_external_id,
        playback_url=playback_url,
        content_url=lesson.content_url,
        embed_url=lesson.embed_url,
        ai_summary=lesson.ai_summary,
        drip_type=lesson.drip_type,
        drip_accessible=drip_accessible,
        drip_reason=drip_reason,
    )


async def update_lesson_progress(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    lesson_id: uuid.UUID,
    body: ProgressUpdate,
) -> LessonProgress:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant_id:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)

    result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    progress = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if progress is None:
        progress = LessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            watch_seconds=body.watch_seconds,
            last_watched_at=now,
            completed_at=now if body.completed else None,
        )
        db.add(progress)
    else:
        progress.watch_seconds = max(progress.watch_seconds, body.watch_seconds)
        progress.last_watched_at = now
        if body.completed and progress.completed_at is None:
            progress.completed_at = now

    await db.commit()
    await db.refresh(progress)
    return progress


async def continue_course(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, course_id: uuid.UUID
) -> ContinueResponse:
    course = await db.get(Course, course_id)
    if course is None or course.tenant_id != tenant_id:
        raise AppError(ErrorCode.COURSE_NOT_FOUND)

    enrolled, _ = await _is_user_enrolled_in_course(db, tenant_id, user_id, course_id)
    if not enrolled:
        raise AppError(ErrorCode.NOT_ENROLLED)

    result = await db.execute(
        select(LessonProgress)
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .where(
            Module.course_id == course_id,
            LessonProgress.user_id == user_id,
            LessonProgress.last_watched_at.isnot(None),
        )
        .order_by(LessonProgress.last_watched_at.desc())
        .limit(1)
    )
    progress = result.scalar_one_or_none()
    return ContinueResponse(
        course_id=course_id,
        lesson_id=progress.lesson_id if progress else None,
    )


async def search_course_transcripts(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, course_id: uuid.UUID, q: str
) -> list[SearchResult]:
    course = await db.get(Course, course_id)
    if course is None or course.tenant_id != tenant_id:
        raise AppError(ErrorCode.COURSE_NOT_FOUND)

    enrolled, _ = await _is_user_enrolled_in_course(db, tenant_id, user_id, course_id)
    if not enrolled:
        raise AppError(ErrorCode.NOT_ENROLLED)

    result = await db.execute(
        select(Lesson, Module.title.label("module_title"))
        .join(Module, Module.id == Lesson.module_id)
        .where(
            Module.course_id == course_id,
            Lesson.tenant_id == tenant_id,
            Lesson.transcript_text.isnot(None),
            func.to_tsvector("portuguese", func.cast(Lesson.transcript_text, Text)).op("@@")(
                func.plainto_tsquery("portuguese", q)
            ),
        )
        .order_by(
            func.ts_rank(
                func.to_tsvector("portuguese", func.cast(Lesson.transcript_text, Text)),
                func.plainto_tsquery("portuguese", q),
            ).desc()
        )
        .limit(20)
    )
    rows = result.all()
    return [
        SearchResult(
            lesson_id=row.Lesson.id,
            lesson_title=row.Lesson.title,
            module_title=row.module_title,
            snippet=None,
        )
        for row in rows
    ]
