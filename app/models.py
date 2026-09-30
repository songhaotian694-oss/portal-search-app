from pydantic import BaseModel, Field
from typing import Any, Annotated

class SyncRequest(BaseModel):
    mode: str = Field(default="mock", pattern="^(mock|test|full|resume|retry)$")
    max_pages: int = Field(default=2, ge=1, le=1000)

class ProcessRequest(BaseModel):
    all_local: bool = False
    build_index: bool = True
    article_ids: list[Annotated[int, Field(gt=0)]] | None = Field(default=None,max_length=10000)

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
