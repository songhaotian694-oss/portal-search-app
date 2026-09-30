"""Aggregate local experience records for the React exploration UI."""
from __future__ import annotations

from collections import Counter
from fastapi import APIRouter, Query
from ..database import db

router = APIRouter(prefix="/api/analytics", tags=["数据分析"])
DIMENSIONS = {"major", "city", "position", "year", "dateYear", "degree"}


def valid(value: object) -> bool:
    return bool(value) and value not in {"待人工核对", "待核对", "未提取", "0"}


def value_for(row: dict, dimension: str) -> str:
    if dimension == "year":
        year = str(row.get("graduation_year") or "")[:4]
        return f"{year} 届" if year.isdigit() else "未提取"
    if dimension == "dateYear":
        year = str(row.get("published_at") or row.get("collected_at") or "")[:4]
        return year if year.isdigit() else "未提取"
    value = str(row.get(dimension) or "未提取")
    return "未提取" if value == "待人工核对" else value


def summarize(rows: list[dict]) -> dict:
    result = {"total": len(rows), "needsReview": sum(bool(row.get("needs_review")) for row in rows)}
    for output, dimension in [("cities", "city"), ("positions", "position"), ("majors", "major"), ("years", "year")]:
        counts = Counter(value_for(row, dimension).replace(" 届", "") if dimension == "year" else value_for(row, dimension) for row in rows)
        result[output] = sorted(([name, count] for name, count in counts.items() if valid(name)), key=lambda item: (-item[1], item[0]))
    return result


def relationships(rows: list[dict], dimensions: list[str]) -> dict:
    nodes: Counter[tuple[str, str]] = Counter()
    links: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        values = [value_for(row, dimension) for dimension in dimensions]
        for dimension, value in zip(dimensions, values):
            nodes[(dimension, value)] += 1
        for index in range(1, len(dimensions)):
            links[(dimensions[index - 1], values[index - 1], dimensions[index], values[index])] += 1
    return {
        "nodes": [{"dimension": dimension, "value": value, "count": count} for (dimension, value), count in nodes.items()],
        "links": [{"fromDimension": first, "fromValue": source, "toDimension": second, "toValue": target, "count": count} for (first, source, second, target), count in links.items()],
    }


@router.get("")
async def analytics(dimensions: str = Query("major,city,position")):
    requested = dimensions.split(",")
    chosen = requested if len(requested) == 3 and all(item in DIMENSIONS for item in requested) and len(set(requested)) == 3 else ["major", "city", "position"]
    rows = db.experience_rows(limit=10000)
    return {"summary": summarize(rows), "relations": relationships(rows, chosen), "dimensions": chosen}
