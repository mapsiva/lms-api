import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.course import Lesson
from app.models.progress import Note

router = APIRouter(tags=["notes"])


class NoteCreate(BaseModel):
    content: str = Field(min_length=1)
    video_timestamp_seconds: Optional[int] = None


class NoteUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    video_timestamp_seconds: Optional[int] = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    lesson_id: uuid.UUID
    content: str
    video_timestamp_seconds: Optional[int]
    created_at: datetime
    updated_at: datetime


@router.get("/lessons/{lesson_id}/notes", response_model=list[NoteResponse])
async def list_notes(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Lesson not found")

    result = await db.execute(
        select(Note)
        .where(Note.user_id == current_user.id, Note.lesson_id == lesson_id)
        .order_by(Note.created_at.asc())
    )
    return result.scalars().all()


@router.post("/lessons/{lesson_id}/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    lesson_id: uuid.UUID,
    body: NoteCreate,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Lesson not found")

    note = Note(
        user_id=current_user.id,
        lesson_id=lesson_id,
        content=body.content,
        video_timestamp_seconds=body.video_timestamp_seconds,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID,
    body: NoteUpdate,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    if note is None or note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Note not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    if note is None or note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Note not found")

    await db.delete(note)
    await db.commit()
