import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.integrations.video.bunny import BunnyVideoProvider
from app.models.course import Course, Lesson, Module
from app.models.user import User
from app.schemas.course import (
    BulkImportRequest,
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    LessonCreate,
    LessonResponse,
    LessonUpdate,
    ModuleCreate,
    ModuleResponse,
    ModuleUpdate,
    ReorderRequest,
)

router = APIRouter(prefix="/admin", tags=["admin:courses"])


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


@router.post("/courses", response_model=CourseResponse, status_code=201)
async def create_course(
    body: CourseCreate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    slug = body.slug or _slugify(body.title)
    slug = await _unique_slug(db, tenant.id, slug)
    course = Course(
        tenant_id=tenant.id,
        slug=slug,
        **{k: v for k, v in body.model_dump(exclude={"slug"}).items()},
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Course).where(Course.tenant_id == tenant.id).order_by(Course.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: uuid.UUID,
    body: CourseUpdate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    course = await db.get(Course, course_id)
    if course is None or course.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Course not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    await db.commit()
    await db.refresh(course)
    return course


@router.post("/courses/{course_id}/modules", response_model=ModuleResponse, status_code=201)
async def create_module(
    course_id: uuid.UUID,
    body: ModuleCreate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    course = await db.get(Course, course_id)
    if course is None or course.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Course not found")
    module = Module(tenant_id=tenant.id, course_id=course_id, **body.model_dump())
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


@router.patch("/modules/{module_id}", response_model=ModuleResponse)
async def update_module(
    module_id: uuid.UUID,
    body: ModuleUpdate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    module = await db.get(Module, module_id)
    if module is None or module.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Module not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(module, field, value)
    await db.commit()
    await db.refresh(module)
    return module


@router.patch("/modules/{module_id}/reorder")
async def reorder_lessons(
    module_id: uuid.UUID,
    body: ReorderRequest,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    module = await db.get(Module, module_id)
    if module is None or module.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Module not found")
    for idx, lesson_id in enumerate(body.lesson_ids):
        await db.execute(
            update(Lesson)
            .where(Lesson.id == lesson_id, Lesson.module_id == module_id, Lesson.tenant_id == tenant.id)
            .values(order_index=idx)
        )
    await db.commit()
    return {"reordered": len(body.lesson_ids)}


@router.post("/modules/{module_id}/lessons", response_model=LessonResponse, status_code=201)
async def create_lesson(
    module_id: uuid.UUID,
    body: LessonCreate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    module = await db.get(Module, module_id)
    if module is None or module.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Module not found")
    lesson = Lesson(tenant_id=tenant.id, module_id=module_id, **body.model_dump())
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


@router.patch("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: uuid.UUID,
    body: LessonUpdate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lesson, field, value)
    await db.commit()
    await db.refresh(lesson)
    return lesson


@router.delete("/lessons/{lesson_id}", status_code=204)
async def delete_lesson(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    await db.delete(lesson)
    await db.commit()


@router.post("/modules/{module_id}/lessons/bulk-import", response_model=list[LessonResponse], status_code=201)
async def bulk_import_lessons(
    module_id: uuid.UUID,
    body: BulkImportRequest,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    module = await db.get(Module, module_id)
    if module is None or module.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Module not found")

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
            tenant_id=tenant.id,
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


@router.get("/bunny/library/{folder}", response_model=list[dict])
async def list_bunny_folder(
    folder: str,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
):
    bunny = BunnyVideoProvider()
    videos = await bunny.list_library_folder(folder)
    return [
        {
            "video_id": v.video_id,
            "title": v.title,
            "duration_seconds": v.duration_seconds,
            "thumbnail_url": v.thumbnail_url,
        }
        for v in videos
    ]


from app.core.celery_app import celery_app  # noqa: E402


@router.post("/lessons/{lesson_id}/transcribe")
async def trigger_transcription(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if lesson.video_provider != "bunny" or not lesson.video_external_id:
        raise HTTPException(status_code=400, detail="Lesson has no Bunny video")
    bunny = BunnyVideoProvider()
    url = await bunny.get_playback_url(lesson.video_external_id, ttl_seconds=7200)
    celery_app.send_task("app.tasks.transcription.transcribe_lesson_task", args=[str(lesson_id), url])
    return {"status": "queued", "lesson_id": str(lesson_id)}


@router.get("/lessons/{lesson_id}/transcript")
async def get_transcript(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if not lesson.transcript_text:
        return {"status": "not_ready", "lesson_id": str(lesson_id), "transcript": None}
    return {"status": "ok", "lesson_id": str(lesson_id), "transcript": lesson.transcript_text}


@router.post("/lessons/{lesson_id}/summarize")
async def trigger_summary(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if not lesson.transcript_text:
        raise HTTPException(status_code=400, detail="Transcript not available")
    celery_app.send_task("app.tasks.transcription.summarize_lesson_task", args=[str(lesson_id)])
    return {"status": "queued", "lesson_id": str(lesson_id)}
