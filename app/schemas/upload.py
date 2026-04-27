"""Schemas for upload routes."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    url: str
