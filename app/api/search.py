from __future__ import annotations

from fastapi import APIRouter, Query

from ..database import db
from .analytics import summarize

router = APIRouter(prefix="/api/search", tags=["选调生搜索"])


@router.get("")
async def search(
    q: str = "",
    graduation_year: str = "",
    degree: str = "",
    major: str = "",
    city: str = "",
    position: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = Query(100, ge=1, le=10000),
):
    filters = {
        "graduation_year": graduation_year,
        "degree": degree,
        "major": major,
        "city": city,
        "position": position,
        "date_from": date_from,
        "date_to": date_to,
    }
    results = db.search_experience_rows(q, filters, limit)
    return {
        "results": results,
        "summary": summarize(results),
        "total_records": db.stats()["valid_records"],
        "city_examples": db.experience_city_examples() if not results else [],
    }
