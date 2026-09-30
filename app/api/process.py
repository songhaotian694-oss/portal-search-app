from __future__ import annotations
import asyncio,json
from pathlib import Path
from fastapi import APIRouter,HTTPException
from ..database import db
from ..models import ProcessRequest
from ..processing.attachment_parser import extract_attachment_text
from ..processing.field_extractor import extract_fields,extract_experience_records,shared_image_relevant,PIPELINE_VERSION,validate_ocr_record
from ..processing.search_index import search_index
from ..settings import DIRS
router=APIRouter(prefix="/api/process",tags=["处理"])
STATE={"status":"idle","current":0,"total":0,"message":""}; task=None
async def run(req:ProcessRequest):
    STATE.update(status="running",current=0,failed=0,message="正在自动识别、拼接与整理本地资料")
    checkpoint=db.checkpoint('process')
    if checkpoint and req.article_ids is None:
        req=ProcessRequest(**checkpoint['request'])
        ids=checkpoint['remaining_ids']
        STATE['current']=checkpoint.get('completed',0)
        STATE['total']=checkpoint['total']
    else:
        ids=req.article_ids if req.article_ids is not None else [row['id'] for row in db.target_articles_to_process(req.all_local)]
        if req.article_ids is None:ids=list(dict.fromkeys([*ids,*[work['payload']['article_id'] for work in db.work_items('process',('pending',))]]))
        STATE['total']=len(ids)
        if checkpoint is None:
            checkpoint={'request':req.model_dump(),'remaining_ids':list(ids),'total':len(ids),'completed':0}
        else:
            extra=[article_id for article_id in ids if article_id not in checkpoint['remaining_ids']]
            checkpoint['remaining_ids'].extend(extra);checkpoint['total']+=len(extra)
        db.save_checkpoint('process',checkpoint)
    rows=[db.get_article(article_id) for article_id in dict.fromkeys(ids)]
    rows=[row for row in rows if row is not None]
    valid_ids={row['id'] for row in rows}
    for article_id in list(ids):
        if article_id not in valid_ids and article_id in checkpoint['remaining_ids']:
            checkpoint['remaining_ids'].remove(article_id)
    db.save_checkpoint('process',checkpoint)
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
            article=db.get_article(row["id"]);sources=[(text,[])];source_failed=False
            for att in article["attachments"]:
                if att["is_external"] or not att["file_path"]:continue
                cache_key=att.get("file_hash") or att["file_path"]
                saved_text=Path(att["text_path"]) if att.get("text_path") else None
                image_or_pdf=Path(att['file_path']).suffix.lower() in {'.png','.jpg','.jpeg','.bmp','.tiff','.tif','.webp','.pdf'}
                if not image_or_pdf and att.get("parse_status") in {"ocr_parsed","parsed"} and saved_text and saved_text.is_file():
                    extra=saved_text.read_text(encoding="utf-8",errors="replace");status=att["parse_status"]
                    attachment_cache[cache_key]=(extra,status)
                elif cache_key in attachment_cache:extra,status=attachment_cache[cache_key]
                else:
                    extra,status=await asyncio.to_thread(extract_attachment_text,Path(att["file_path"]));attachment_cache[cache_key]=(extra,status)
                if status in {'failed','ocr_empty'}:
                    source_failed=True;STATE['failed']+=1
                    db.add_failure(None,'attachment:'+str(att['id']),'auto_recognition',status)
                    db.update_attachment_parse(att['id'],status,None);continue
                db.resolve_failures('attachment:'+str(att['id']),('auto_recognition',))
                # 共享海报按内容归属到首篇匹配的通知，防止同地区另一篇重复计数。
                if att.get("file_hash") in shared_hashes:
                    owner=next((article_id for article_id,title in shared_articles[att["file_hash"]]
                                if shared_image_relevant(title,extra)),None)
                    if row["id"]!=owner:
                        db.update_attachment_parse(att["id"],"shared_image_skipped",None);continue
                out=DIRS["extracted_text"]/(str(att["id"])+".txt")
                out.write_text(extra,encoding="utf-8");db.update_attachment_parse(att["id"],status,str(out));text += "\n"+extra
                cache=Path(att['file_path']).with_suffix(Path(att['file_path']).suffix+'.ocr.json')
                try:proof=json.loads(cache.read_text(encoding='utf-8')).get('lines',[]) if cache.is_file() else []
                except (ValueError,OSError):proof=[]
                sources.append((extra,proof))
            db.save_record(row["id"],extract_fields(text));db.update_fts(row["id"],row["title"],text)
            records=[];seen=set()
            for source,proof in sources:
                for record in extract_experience_records(source,row['title']):
                    if proof:record=validate_ocr_record(record,proof)
                    key=tuple(record.get(k) for k in ('student_name','graduation_year','grade','major','employer','position'))
                    if key not in seen:records.append(record);seen.add(key)
            # An unreadable attachment must not erase the previous successful result.
            if not source_failed:db.replace_experience_records(row["id"],records)
            if req.build_index: await asyncio.to_thread(search_index.index_article,row["id"],text)
            STATE["current"]+=1
            if not source_failed:
                db.finish_work('process',str(row['id']))
                if row['id'] in checkpoint['remaining_ids']:
                    checkpoint['remaining_ids'].remove(row['id']);checkpoint['completed']+=1
                db.save_checkpoint('process',checkpoint)
            await asyncio.sleep(0)
        if not checkpoint['remaining_ids']:
            if checkpoint['request']['all_local']:db.set_metadata('pipeline_version',PIPELINE_VERSION)
            db.save_checkpoint('process',None)
        STATE.update(status="paused" if checkpoint['remaining_ids'] else "completed",message=f"{STATE['failed']} 个附件暂未识别，已保存进度，可继续识别或重试失败项" if STATE['failed'] else "自动整理完成，缺失字段已保留为空")
        if checkpoint['remaining_ids'] and not STATE['failed']:STATE['message']='本次识别完成，上次任务仍有未完成文章，可继续识别'
    except Exception as e:STATE.update(status="failed",message=f"处理失败：{type(e).__name__}: {e}")
@router.post("/start")
async def start(req:ProcessRequest):
    global task
    if task and not task.done():return STATE
    from . import sync
    if sync.task and not sync.task.done() and sync.task is not asyncio.current_task():raise HTTPException(409,'资料正在下载，完成后会自动识别')
    # Persist before scheduling so shutdown between sync completion and OCR
    # startup cannot leave newly downloaded articles without a recovery task.
    saved=db.checkpoint('process')
    from_sync=sync.task is asyncio.current_task()
    if saved is None or (req.all_local and not from_sync):
        ids=req.article_ids if req.article_ids is not None else [row['id'] for row in db.target_articles_to_process(req.all_local)]
        if req.article_ids is None:ids=list(dict.fromkeys([*ids,*[work['payload']['article_id'] for work in db.work_items('process',('pending',))]]))
        db.save_checkpoint('process',{'request':req.model_dump(),'remaining_ids':list(ids),'total':len(ids),'completed':0})
    elif req.article_ids is None and from_sync:
        candidates=[row['id'] for row in db.target_articles_to_process(req.all_local)]+[work['payload']['article_id'] for work in db.work_items('process',('pending',))]
        extra=[article_id for article_id in dict.fromkeys(candidates) if article_id not in saved['remaining_ids']]
        saved['remaining_ids'].extend(extra);saved['total']+=len(extra)
        db.save_checkpoint('process',saved)
    STATE.update(status='running',current=0,total=0,message='自动整理已启动')
    task=asyncio.create_task(run(req));return STATE
@router.get("/status")
async def status():
    saved=db.checkpoint('process')
    if saved and STATE['status']=='idle':
        return {**STATE,'status':'paused','current':saved.get('completed',0),'total':saved['total'],'message':'上次识别尚未完成，登录后会自动继续','resume_available':True}
    return {**STATE,'resume_available':bool(saved)}
