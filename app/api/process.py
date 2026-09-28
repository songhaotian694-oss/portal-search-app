from __future__ import annotations
import asyncio
from pathlib import Path
from fastapi import APIRouter
from ..database import db
from ..models import ProcessRequest
from ..processing.attachment_parser import extract_attachment_text
from ..processing.field_extractor import extract_fields,extract_experience_records,shared_image_relevant
from ..processing.search_index import search_index
from ..settings import DIRS
router=APIRouter(prefix="/api/process",tags=["处理"])
STATE={"status":"idle","current":0,"total":0,"message":""}; task=None
async def run(req:ProcessRequest):
    STATE.update(status="running",current=0,message="正在读取本地正文和附件")
    rows=db.target_articles_to_process(req.all_local);STATE["total"]=len(rows)
    try:
        attachment_cache={}
        with db.connection() as connection:
            shared_hashes={x["file_hash"] for x in connection.execute(
                "SELECT file_hash FROM attachments WHERE file_hash IS NOT NULL GROUP BY file_hash HAVING count(DISTINCT article_id)>1"
            )}
            shared_articles={hash_value:[(x["article_id"],x["title"]) for x in connection.execute(
                "SELECT t.article_id,a.title FROM attachments t JOIN articles a ON a.id=t.article_id WHERE t.file_hash=? ORDER BY t.article_id",
                (hash_value,))] for hash_value in shared_hashes}
        for row in rows:
            text=Path(row["text_path"]).read_text(encoding="utf-8",errors="replace") if row["text_path"] else ""
            article=db.get_article(row["id"])
            for att in article["attachments"]:
                if att["is_external"] or not att["file_path"]:continue
                cache_key=att.get("file_hash") or att["file_path"]
                saved_text=Path(att["text_path"]) if att.get("text_path") else None
                if att.get("parse_status") in {"ocr_parsed","parsed"} and saved_text and saved_text.is_file():
                    extra=saved_text.read_text(encoding="utf-8",errors="replace");status=att["parse_status"]
                    attachment_cache[cache_key]=(extra,status)
                elif cache_key in attachment_cache:extra,status=attachment_cache[cache_key]
                else:
                    extra,status=await asyncio.to_thread(extract_attachment_text,Path(att["file_path"]));attachment_cache[cache_key]=(extra,status)
                # 共享海报按内容归属到首篇匹配的通知，防止同地区另一篇重复计数。
                if att.get("file_hash") in shared_hashes:
                    owner=next((article_id for article_id,title in shared_articles[att["file_hash"]]
                                if shared_image_relevant(title,extra)),None)
                    if row["id"]!=owner:
                        db.update_attachment_parse(att["id"],"shared_image_skipped",None);continue
                out=DIRS["extracted_text"]/(str(att["id"])+".txt")
                out.write_text(extra,encoding="utf-8");db.update_attachment_parse(att["id"],status,str(out));text += "\n"+extra
            db.save_record(row["id"],extract_fields(text));db.update_fts(row["id"],row["title"],text)
            db.replace_experience_records(row["id"],extract_experience_records(text,row["title"]))
            if req.build_index: await asyncio.to_thread(search_index.index_article,row["id"],text)
            STATE["current"]+=1;await asyncio.sleep(0)
        STATE.update(status="completed",message=("已完成；"+(search_index.error or "关键词及语义索引已建立")))
    except Exception as e:STATE.update(status="failed",message=f"处理失败：{type(e).__name__}: {e}")
@router.post("/start")
async def start(req:ProcessRequest):
    global task
    if task and not task.done():return STATE
    task=asyncio.create_task(run(req));return STATE
@router.get("/status")
async def status():return STATE
