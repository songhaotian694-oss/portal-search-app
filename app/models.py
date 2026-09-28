from pydantic import BaseModel, Field
from typing import Any

class SyncRequest(BaseModel):
    mode: str = Field(default="mock", pattern="^(mock|test|full|resume)$")
    max_pages: int = Field(default=2, ge=1, le=1000)

class ProcessRequest(BaseModel):
    all_local: bool = False
    build_index: bool = True

class ReviewRequest(BaseModel):
    graduation_year: str | None = None
    grade: str | None = None
    degree: str | None = None
    major: str | None = None
    city: str | None = None
    employer: str | None = None
    position: str | None = None
    evidence_sentence: str | None = None
    needs_review: bool = False

class SettingsUpdate(BaseModel):
    values: dict[str, Any]
