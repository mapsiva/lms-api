import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app  # noqa: F401
from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.integrations.video.bunny import BunnyVideoProvider  # noqa: F401
from app.models.user import User
from app.schemas.course import (
    BulkImportRequest,
    BunnyVideoItem,
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
    ReorderResponse,
    TranscriptResponse,
    TranscriptionQueueResponse,
)
from app.services import admin_course as admin_course_service

router = APIRouter(prefix="/admin", tags=["admin:courses"])


@router.post("/courses", response_model=CourseResponse, status_code=201)
async def create_course(
    body: CourseCreate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.create_course(db, tenant.id, body)


@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.list_courses(db, tenant.id)


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.get_course(db, tenant.id, course_id)


@router.patch("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: uuid.UUID,
    body: CourseUpdate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.update_course(db, tenant.id, course_id, body)


@router.post("/courses/{course_id}/modules", response_model=ModuleResponse, status_code=201)
async def create_module(
    course_id: uuid.UUID,
    body: ModuleCreate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.create_module(db, tenant.id, course_id, body)


@router.patch("/modules/{module_id}", response_model=ModuleResponse)
async def update_module(
    module_id: uuid.UUID,
    body: ModuleUpdate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.update_module(db, tenant.id, module_id, body)


@router.patch("/modules/{module_id}/reorder", response_model=ReorderResponse)
async def reorder_lessons(
    module_id: uuid.UUID,
    body: ReorderRequest,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.reorder_lessons(db, tenant.id, module_id, body)


@router.post("/modules/{module_id}/lessons", response_model=LessonResponse, status_code=201)
async def create_lesson(
    module_id: uuid.UUID,
    body: LessonCreate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.create_lesson(db, tenant.id, module_id, body)


@router.patch("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: uuid.UUID,
    body: LessonUpdate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.update_lesson(db, tenant.id, lesson_id, body)


@router.delete("/lessons/{lesson_id}", status_code=204)
async def delete_lesson(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await admin_course_service.delete_lesson(db, tenant.id, lesson_id)


@router.post("/modules/{module_id}/lessons/bulk-import", response_model=list[LessonResponse], status_code=201)
async def bulk_import_lessons(
    module_id: uuid.UUID,
    body: BulkImportRequest,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.bulk_import_lessons(db, tenant.id, module_id, body)


@router.get("/bunny/library/{folder}", response_model=list[BunnyVideoItem])
async def list_bunny_folder(
    folder: str,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
):
    return await admin_course_service.list_bunny_folder(folder)


@router.post("/lessons/{lesson_id}/transcribe", response_model=TranscriptionQueueResponse)
async def trigger_transcription(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.trigger_transcription(db, tenant.id, lesson_id)


@router.get("/lessons/{lesson_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.get_transcript(db, tenant.id, lesson_id)


@router.post("/lessons/{lesson_id}/summarize", response_model=TranscriptionQueueResponse)
async def trigger_summary(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_course_service.trigger_summary(db, tenant.id, lesson_id)
