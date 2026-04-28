import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.course import Lesson
from app.models.progress import Note
from app.schemas.note import NoteCreate, NoteUpdate


async def list_notes(
    db: AsyncSession,
    lesson_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> list[Note]:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant_id:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)

    result = await db.execute(
        select(Note)
        .where(Note.user_id == user_id, Note.lesson_id == lesson_id)
        .order_by(Note.created_at.asc())
    )
    return list(result.scalars().all())


async def create_note(
    db: AsyncSession,
    lesson_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    body: NoteCreate,
) -> Note:
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None or lesson.tenant_id != tenant_id:
        raise AppError(ErrorCode.LESSON_NOT_FOUND)

    note = Note(
        user_id=user_id,
        lesson_id=lesson_id,
        content=body.content,
        video_timestamp_seconds=body.video_timestamp_seconds,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def update_note(
    db: AsyncSession,
    note_id: uuid.UUID,
    user_id: uuid.UUID,
    body: NoteUpdate,
) -> Note:
    note = await db.get(Note, note_id)
    if note is None or note.user_id != user_id:
        raise AppError(ErrorCode.NOTE_NOT_FOUND)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(
    db: AsyncSession,
    note_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    note = await db.get(Note, note_id)
    if note is None or note.user_id != user_id:
        raise AppError(ErrorCode.NOTE_NOT_FOUND)

    await db.delete(note)
    await db.commit()
