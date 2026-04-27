import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.integrations.video.bunny import BunnyVideoProvider  # noqa: F401
from app.schemas.course import (
    ContinueResponse,
    CourseDetail,
    CourseListItem,
    LessonDetailResponse,
    ProgressResponse,
    ProgressUpdate,
    SearchResult,
)
from app.services import course as course_service

router = APIRouter(tags=["courses"])


@router.get("/courses", response_model=list[CourseListItem])
async def list_enrolled_courses(
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await course_service.list_enrolled_courses(db, tenant.id, current_user.id)


@router.get("/courses/{slug}", response_model=CourseDetail)
async def get_course(
    slug: str,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await course_service.get_course_detail(db, tenant.id, current_user.id, slug)


@router.get("/lessons/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await course_service.get_lesson_detail(
        db, tenant.id, current_user.id, lesson_id, bunny_provider=BunnyVideoProvider
    )


@router.post("/lessons/{lesson_id}/progress", response_model=ProgressResponse)
async def update_lesson_progress(
    lesson_id: uuid.UUID,
    body: ProgressUpdate,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await course_service.update_lesson_progress(
        db, tenant.id, current_user.id, lesson_id, body
    )


@router.get("/courses/{course_id}/continue", response_model=ContinueResponse)
async def continue_course(
    course_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await course_service.continue_course(db, tenant.id, current_user.id, course_id)


@router.get("/courses/{course_id}/search", response_model=list[SearchResult])
async def search_course_transcripts(
    course_id: uuid.UUID,
    q: str = Query(min_length=1),
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await course_service.search_course_transcripts(
        db, tenant.id, current_user.id, course_id, q
    )
