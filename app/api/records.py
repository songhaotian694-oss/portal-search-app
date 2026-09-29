from fastapi import APIRouter,Query
from ..database import db

router=APIRouter(prefix="/api/records",tags=["有效就业数据"])

@router.get("")
async def records(limit:int=Query(300,ge=1,le=10000)):
    return {"results":db.experience_rows(limit)}
