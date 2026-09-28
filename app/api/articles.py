from fastapi import APIRouter,HTTPException
from ..database import db
from ..models import ReviewRequest
router=APIRouter(prefix="/api/articles",tags=["文章"])
@router.get("/{article_id}")
async def detail(article_id:int):
    a=db.get_article(article_id)
    if not a:raise HTTPException(404,"文章不存在")
    try:
        from pathlib import Path
        a["text_preview"]=Path(a["text_path"]).read_text(encoding="utf-8",errors="replace")[:8000] if a.get("text_path") else ""
    except OSError:a["text_preview"]="正文文件不可读"
    return a
@router.put("/{article_id}/review")
async def review(article_id:int, req:ReviewRequest):
    if not db.get_article(article_id):raise HTTPException(404,"文章不存在")
    db.review_article(article_id,req.model_dump());return {"ok":True}
