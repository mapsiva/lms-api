import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from app.services import note as note_service

router = APIRouter(tags=["notes"])


@router.get("/lessons/{lesson_id}/notes", response_model=list[NoteResponse])
async def list_notes(
    lesson_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.list_notes(db, lesson_id, current_user.id, tenant.id)


@router.post("/lessons/{lesson_id}/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    lesson_id: uuid.UUID,
    body: NoteCreate,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.create_note(db, lesson_id, current_user.id, tenant.id, body)


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: uuid.UUID,
    body: NoteUpdate,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.update_note(db, note_id, current_user.id, body)


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await note_service.delete_note(db, note_id, current_user.id)
