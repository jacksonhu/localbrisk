"""Shared request and response models for business unit endpoints."""

from pydantic import BaseModel


class OutputFileContentResponse(BaseModel):
    """Output file content response."""

    path: str
    relative_path: str
    content: str


class OutputFileSaveRequest(BaseModel):
    """Save output file content request."""

    path: str
    content: str


class SkillImportRequest(BaseModel):
    """Skill import request."""

    zip_file_path: str
