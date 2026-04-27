"""Internal callback routes (not public API)."""
import logging

from fastapi import APIRouter, Request

from app.schemas.internal import TranscriptionCallbackResponse
from app.services.internal import process_transcription_callback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/transcription-callback", response_model=TranscriptionCallbackResponse)
async def transcription_callback(request: Request):
    """AssemblyAI webhook callback: save transcript, trigger summary."""
    auth_header = request.headers.get("authorization", "")
    body = await request.json()
    result = await process_transcription_callback(auth_header=auth_header, body=body)
    return TranscriptionCallbackResponse(status=result["status"], lesson_id=result["lesson_id"])
