import re
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.integrations.video.bunny import BunnyVideoProvider
from app.models.course import Course, Lesson, Module
from app.schemas.course import (
    BunnyVideoItem,
    BulkImportRequest,
    CourseCreate,
    CourseUpdate,
    LessonCreate,
    LessonUpdate,
    ModuleCreate,
    ModuleUpdate,
    ReorderRequest,
    ReorderResponse,
    TranscriptResponse,
    TranscriptionQueueResponse,
)


def _slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug[:255]


async def _unique_slug(db: AsyncSession, tenant_id: uuid.UUID, base: str) -> str:
    candidate = base
    counter = 1
    while True:
        result = await db.execute(
            select(Course).where(Course.tenant_id == tenant_id, Course.slug == candidate)
        )
        if result.scalar_one_or_none() is None:
            return candidate
        candidate = f"{base}-{counter}"
        counter += 1


async def create_course(
    db: AsyncSession, tenant_id: uuid.UUID, body: CourseCreate
) -> Course:
    slug = body.slug or _slugify(body.title)
    slug = await _unique_slug(db, tenant_id, slug)
    course = Course(
        tenant_id=tenant_id,
        slug=slug,
        **{k: v for k, v in body.model_dump(exclude={"slug"}).items()},
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


async def list_courses(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[Course]:
    result = await db.execute(
        select(Course).where(Course.tenant_id == tenant_id).order_by(Course.created_at.desc())
    )
    return list(result.scalars().all())


async def update_course(
    db: AsyncSession, tenant_id: uuid.UUID, course_id: uuid.UUID, body: CourseUpdate
) -> Course:
    course = await db.get(Course, course_id)
    if course is None or course.tenant_id != tenant_id:
        raise AppError(ErrorCode.COURSE_NOT_FOUND)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    await db.commit()
    await db.refresh(course)
    return course


async def create_module(
    db: AsyncSession, tenant_id: uuid.UUID, course_id: uuid.UUID, body: ModuleCreate
) -> Module:
    course = await db.get(Course, course_id)
    if course is None or course.tenant_id != tenant_id:
        raise AppError(ErrorCode.COURSE_NOT_FOUND)
    module = Module(tenant_id=tenant_id, course_id=course_id, **body.model_dump())
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


async def update_module(
    db: AsyncSession, tenant_id: uuid.UUID, module_id: uuid.UUID, body: ModuleUpdate
) -> Module:
    module = await db.get(Module, module_id)
    if module is None or module.tenant_id != tenant_id:
        raise AppError(ErrorCode.MODULE_NOT_FOUND)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(module, field, value)
    await db.commit()
    await db.refresh(module)
    return module


async def reorder_lessons(
    db: AsyncSession, tenant_id: uuid.UUID, module_id: uuid.UUID, body: ReorderRequest
) -> ReorderResponse:
    module = await db.get(Module, module_id)
    if module is None or module.tenant_id != tenant_id:
        raise AppError(ErrorCode.MODULE_NOT_FOUND)
    for idx, lesson_id in enumerate(body.lesson_ids):
        await db.execute(
            update(Lesson)
            .where(Lesson.id == lesson_id, Lesson.module_id == module_id, Lesson.tenant_id == tenant_id)
            .values(order_index=idx)
        )
    await db.commit()
    return ReorderResponse(reordered=len(body.lesson_ids))


async def create_lesson(
    db: AsyncSession, tenant_id: uuid.UUID, module_id: uuid.UUID, body: LessonCreate
) -> Lesson:
    module = await db.get(Module, module_id)
    if module is None or module.tenant_id != tenant_id:
        raise AppError(ErrorCode.MODULE_NOT_FOUND)
    lesson = Lesson(tenant_id=tenant_id, module_id=module_id, **body.model_dump())
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def update_lesson(
    db: AsyncSession, tenant_id: uuid.UUID, lesson_id: uuid.UUID, body: LessonUpdate
) -> Lesson:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant_id:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lesson, field, value)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def delete_lesson(
    db: AsyncSession, tenant_id: uuid.UUID, lesson_id: uuid.UUID
) -> None:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant_id:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)
    await db.delete(lesson)
    await db.commit()


async def bulk_import_lessons(
    db: AsyncSession, tenant_id: uuid.UUID, module_id: uuid.UUID, body: BulkImportRequest
) -> list[Lesson]:
    module = await db.get(Module, module_id)
    if module is None or module.tenant_id != tenant_id:
        raise AppError(ErrorCode.MODULE_NOT_FOUND)

    bunny = BunnyVideoProvider()
    videos = await bunny.list_library_folder(body.folder)

    result = await db.execute(
        select(Lesson.order_index)
        .where(Lesson.module_id == module_id)
        .order_by(Lesson.order_index.desc())
        .limit(1)
    )
    max_order = result.scalar_one_or_none() or -1

    lessons = []
    for i, video in enumerate(videos):
        lesson = Lesson(
            tenant_id=tenant_id,
            module_id=module_id,
            title=video.title or video.video_id,
            lesson_type="video",
            order_index=max_order + 1 + i,
            video_provider="bunny",
            video_external_id=video.video_id,
            duration_seconds=video.duration_seconds,
        )
        db.add(lesson)
        lessons.append(lesson)

    await db.commit()
    for lesson in lessons:
        await db.refresh(lesson)
    return lessons


async def list_bunny_folder(folder: str) -> list[BunnyVideoItem]:
    bunny = BunnyVideoProvider()
    videos = await bunny.list_library_folder(folder)
    return [
        BunnyVideoItem(
            video_id=v.video_id,
            title=v.title,
            duration_seconds=v.duration_seconds,
            thumbnail_url=v.thumbnail_url,
        )
        for v in videos
    ]


async def trigger_transcription(
    db: AsyncSession, tenant_id: uuid.UUID, lesson_id: uuid.UUID
) -> TranscriptionQueueResponse:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant_id:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)
    if lesson.video_provider != "bunny" or not lesson.video_external_id:
        raise AppError(ErrorCode.LESSON_NO_VIDEO)
    bunny = BunnyVideoProvider()
    url = await bunny.get_playback_url(lesson.video_external_id, ttl_seconds=7200)
    celery_app.send_task("app.tasks.transcription.transcribe_lesson_task", args=[str(lesson_id), url])
    return TranscriptionQueueResponse(status="queued", lesson_id=str(lesson_id))


async def get_transcript(
    db: AsyncSession, tenant_id: uuid.UUID, lesson_id: uuid.UUID
) -> TranscriptResponse:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant_id:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)
    if not lesson.transcript_text:
        return TranscriptResponse(status="not_ready", lesson_id=str(lesson_id), transcript=None)
    return TranscriptResponse(status="ok", lesson_id=str(lesson_id), transcript=lesson.transcript_text)


async def trigger_summary(
    db: AsyncSession, tenant_id: uuid.UUID, lesson_id: uuid.UUID
) -> TranscriptionQueueResponse:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant_id:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)
    if not lesson.transcript_text:
        raise AppError(ErrorCode.TRANSCRIPT_NOT_AVAILABLE)
    celery_app.send_task("app.tasks.transcription.summarize_lesson_task", args=[str(lesson_id)])
    return TranscriptionQueueResponse(status="queued", lesson_id=str(lesson_id))
