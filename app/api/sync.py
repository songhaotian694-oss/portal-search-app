from __future__ import annotations
import asyncio, hashlib, json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from ..database import db
from ..models import SyncRequest
from ..settings import RESOURCE_ROOT,DIRS,load_config,is_allowed_url
from ..crawler.browser_session import browser_session
from ..crawler.portal_adapter import PortalAdapter
from ..crawler.article_downloader import save_article,save_api_article
from ..crawler.portal_api import (
    PortalApiError, capture_first_page, extract_rows, fetch_page,
    normalize_notice, save_raw_page,
)
from ..processing.html_parser import clean_html,extract_attachments
from ..processing.field_extractor import extract_fields
router=APIRouter(prefix="/api/sync",tags=["同步"])
STATE={"status":"idle","current":0,"total":0,"success":0,"failed":0,"message":""}; task=None
MOCK_CONFIG={"list_item_selector":".item","title_selector":".title","date_selector":".date","detail_link_selector":".title","next_button_selector":".next","detail_body_selector":".article-body","attachment_selector":".attachment"}
FIX=RESOURCE_ROOT/"tests"/"fixtures"

def checkpoint_progress(**values):
    saved=db.checkpoint('sync')
    if saved:
        saved.update(values)
        saved['progress']=dict(STATE)
        db.save_checkpoint('sync',saved)

async def download_work(work:dict,job:int,page,cfg:dict,track_checkpoint:bool=True):
    payload=work['payload'];item=dict(payload['item']);url=item['detail_url']
    article_id=None
    try:
        if payload['source']=='api_mapping':
            item=normalize_notice(payload['row'],cfg);raw=item.pop('raw_api');url=item['detail_url']
            payload={'item':item,'row':raw,'source':'api'}
            db.queue_work('sync',work['item_key'],payload)
            db.resolve_failures(work['item_key'],('api_mapping',))
        if payload['source']=='api':saved,attachments=await save_api_article(page,item,payload['row'],cfg)
        else:saved,attachments=await save_article(page,item,cfg)
        aid,changed=db.upsert_article(saved)
        for attachment in attachments:db.add_attachment(aid,attachment)
        if changed and '选调' in saved.get('title','') and '经验分享' in saved.get('title',''):
            db.queue_work('process',str(aid),{'article_id':aid})
        make_searchable(aid,saved)
        db.finish_work('sync',work['item_key'])
        db.resolve_failures(url,('api_download','download','mock'))
        STATE['success']+=1
        article_id=aid
    except Exception as exc:
        db.finish_work('sync',work['item_key'],str(exc))
        stage='api_mapping' if payload['source']=='api_mapping' else 'api_download' if payload['source']=='api' else 'download'
        db.add_failure(job,url,stage,str(exc))
        STATE['failed']+=1
    STATE['current']+=1
    if track_checkpoint:checkpoint_progress()
    await asyncio.sleep(float(cfg.get('page_interval_seconds',1.5)))
    return article_id

async def drain_work(job:int,page,cfg:dict):
    for work in db.work_items('sync',('pending',)):
        await download_work(work,job,page,cfg)

def queue_item(item:dict,source:str,row:dict|None=None):
    db.queue_work('sync',item['detail_url'],{'item':item,'source':source,'row':row})
def hash_text(x:str):return hashlib.sha256(x.encode()).hexdigest()
def make_searchable(article_id:int,item:dict):
    """正文一落盘就建立轻量本地索引，让用户无需等待后续处理即可搜索。"""
    path=item.get("text_path")
    text=Path(path).read_text(encoding="utf-8",errors="replace") if path else ""
    db.update_fts(article_id,item.get("title",""),text)
    db.save_record(article_id,extract_fields(text))
async def mock_sync(req:SyncRequest,job:int):
    items=PortalAdapter(MOCK_CONFIG).parse_list((FIX/"list.html").read_text(encoding="utf-8"),"https://mock.local/")
    STATE["total"]=len(items)
    for item in items:
        try:
            detail=FIX/(Path(item["detail_url"]).name);html=detail.read_text(encoding="utf-8"); key=hash_text(item["detail_url"])[:16]
            raw=DIRS["raw_html"]/(key+".html");txt=DIRS["article_text"]/(key+".txt");raw.write_text(html,encoding="utf-8");text=clean_html(html,".article-body");txt.write_text(text,encoding="utf-8")
            item.update(raw_html_path=str(raw),text_path=str(txt),content_hash=hash_text(text),download_status="done")
            aid,_=db.upsert_article(item)
            # 模拟 Word 附件由本地生成，仅用于测试附件处理，不含编造门户数据。
            for link in extract_attachments(html,item["detail_url"],".attachment"):
                from docx import Document
                p=DIRS["attachments"]/(key+"_经验材料.docx");doc=Document();doc.add_paragraph("附件补充：2024届本科生在北京就业，已入职基层公务员岗位。");doc.save(p)
                db.add_attachment(aid,{"name":"经验材料.docx","file_path":str(p),"file_type":".docx","file_hash":hashlib.sha256(p.read_bytes()).hexdigest()})
            STATE["success"]+=1
        except Exception as e:db.add_failure(job,item.get("detail_url",""),"mock",str(e));STATE["failed"]+=1
        STATE["current"]+=1;await asyncio.sleep(.05)
async def portal_sync(req:SyncRequest,job:int):
    ok,_=await browser_session.is_logged_in()
    if not ok:raise RuntimeError("登录已过期或尚未确认登录，请先手动重新登录")
    cfg=load_config();page=browser_session.page;url=cfg["employment_entry"]
    if not is_allowed_url(url,cfg):raise RuntimeError("就业栏目地址不在允许域名中；请在 portal.yaml 填写真实域名")
    if req.mode=='retry':
        await retry_failed_items(job,page,cfg)
        return
    await drain_work(job,page,cfg)
    source=(db.checkpoint('sync') or {}).get('source')
    if cfg.get("data_source") in {"api","auto"} and source not in {'page','spa'}:
        try:
            await api_portal_sync(req,job,page,cfg,url)
            return
        except PortalApiError as exc:
            if (db.checkpoint('sync') or {}).get('source')=='api':raise
            STATE["message"]=f"接口模式不可用，已切换页面模式：{exc}"
    if source=='spa' or (source!='page' and cfg.get("detail_open_mode") == "click"):
        await spa_portal_sync(req,job,page,cfg,url)
        return
    saved_checkpoint=db.checkpoint('sync') or {}
    adapter=PortalAdapter(cfg);pages=saved_checkpoint.get('page_offset',0)
    url=saved_checkpoint.get('next_url',url)
    while url and pages<req.max_pages:
        await page.goto(url,wait_until="domcontentloaded");html=await page.content();items=adapter.parse_list(html,url);STATE["total"]+=len(items)
        url=adapter.next_url(html,url);pages+=1
        db.stage_sync_page([{'item':item,'source':'page','row':None} for item in items],{'source':'page','next_url':url,'page_offset':pages},STATE)
        await drain_work(job,page,cfg)

async def api_portal_sync(req:SyncRequest,job:int,page,cfg:dict,url:str):
    """复用登录会话直接调用门户JSON接口，页面抓取仅作为后备。"""
    initial_result,template=await capture_first_page(page,url)
    STATE["message"]="已捕获 getNoticeByPage，正在直接读取接口正文（无需逐条打开）"
    keywords=cfg.get("api_keywords") or [""]
    if isinstance(keywords,str):keywords=[keywords]
    saved_checkpoint=db.checkpoint('sync') or {}
    start_keyword=saved_checkpoint.get('keyword_index',0)
    start_page=saved_checkpoint.get('page_offset',0)
    checkpoint_progress(source='api')
    for keyword_index in range(start_keyword,len(keywords)):
        keyword=keywords[keyword_index]
        for page_offset in range(start_page if keyword_index==start_keyword else 0,req.max_pages):
            if not keyword and page_offset==0:
                result=initial_result
            else:
                result=await fetch_page(page,template,page_offset,keyword or None)
            save_raw_page(result,keyword,page_offset+1)
            rows=extract_rows(result)
            if not rows:
                checkpoint_progress(keyword_index=keyword_index+1,page_offset=0)
                break
            items=[]
            payloads=[]
            for row in rows:
                try:
                    item=normalize_notice(row,cfg)
                    items.append(item)
                except PortalApiError as exc:
                    key='api-row:'+hash_text(json.dumps(row,sort_keys=True,ensure_ascii=False))
                    payloads.append({'item':{'detail_url':key},'source':'api_mapping','row':row})
                    db.add_failure(job,key,"api_mapping",str(exc))
            STATE["total"]+=len(rows)
            # Persist the whole page before advancing its cursor. If the app
            # exits during a download, the remaining records survive restart.
            for item in items:
                row=item.pop('raw_api');payloads.append({'item':item,'source':'api','row':row})
            db.stage_sync_page(payloads,{'source':'api','keyword_index':keyword_index,'page_offset':page_offset+1},STATE)
            await drain_work(job,page,cfg)

async def spa_portal_sync(req:SyncRequest,job:int,page,cfg:dict,url:str):
    """处理标题没有 href、详情和翻页均由 Vue 点击事件驱动的门户页面。"""
    item_selector=cfg["list_item_selector"]
    title_selector=cfg["title_selector"]
    date_selector=cfg["date_selector"]
    next_selector=cfg["next_button_selector"]
    await page.goto(url,wait_until="domcontentloaded")
    await page.locator(item_selector).first.wait_for(state="visible",timeout=15000)
    saved_checkpoint=db.checkpoint('sync') or {}
    resume_page=saved_checkpoint.get('page_offset',0)
    resume_row=saved_checkpoint.get('row_index',0)
    pages=0
    while pages<req.max_pages:
        list_url=page.url
        rows=page.locator(item_selector)
        row_count=await rows.count()
        if pages>=resume_page:STATE["total"]+=row_count
        indices=range(resume_row if pages==resume_page else 0,row_count) if pages>=resume_page else []
        for index in indices:
            detail_page=None
            item=None
            try:
                # 返回列表后 DOM 会重建，所以每次重新取得 locator。
                row=page.locator(item_selector).nth(index)
                title=(await row.locator(title_selector).inner_text()).strip()
                date_node=row.locator(date_selector)
                published_at=(await date_node.inner_text()).strip() if await date_node.count() else ""
                before_pages=set(page.context.pages)
                await row.locator(title_selector).click()
                new_pages=[]
                for _ in range(20):
                    new_pages=[item for item in page.context.pages if item not in before_pages and not item.is_closed()]
                    if new_pages:break
                    await page.wait_for_timeout(100)
                detail_page=new_pages[-1] if new_pages else page
                try:await detail_page.wait_for_load_state("domcontentloaded",timeout=5000)
                except Exception:pass
                await detail_page.locator(".print_main").wait_for(state="visible",timeout=15000)
                detail_url=detail_page.url
                item={"portal_id":hash_text(detail_url)[:24],"title":title,"published_at":published_at,"detail_url":detail_url,"category":"就业信息"}
                queue_item(item,'page')
                saved,attachments=await save_article(detail_page,item,cfg,navigate=False);aid,changed=db.upsert_article(saved)
                for attachment in attachments:db.add_attachment(aid,attachment)
                if changed and '选调' in title and '经验分享' in title:db.queue_work('process',str(aid),{'article_id':aid})
                make_searchable(aid,saved)
                db.finish_work('sync',detail_url)
                db.resolve_failures(detail_url,('download',))
                STATE["success"]+=1
            except Exception as e:
                if item:
                    db.finish_work('sync',item['detail_url'],str(e))
                    db.add_failure(job,item['detail_url'],'download',str(e))
                else:
                    # Keep the cursor on this row when it cannot be identified.
                    checkpoint_progress(source='spa',page_offset=pages,row_index=index)
                    raise
                STATE["failed"]+=1
            finally:
                if detail_page is not None and detail_page is not page and not detail_page.is_closed():
                    await detail_page.close()
                STATE["current"]+=1
                if item:checkpoint_progress(source='spa',page_offset=pages,row_index=index+1)
                if page.url != list_url:
                    await page.goto(list_url,wait_until="domcontentloaded")
                    await page.locator(item_selector).first.wait_for(state="visible",timeout=15000)
                await asyncio.sleep(float(cfg.get("page_interval_seconds",1.5)))

        pages+=1
        if pages>resume_page:checkpoint_progress(source='spa',page_offset=pages,row_index=0)
        if pages>=req.max_pages:break
        next_button=page.locator(next_selector).first
        if not await next_button.count() or await next_button.is_disabled():break
        old_first=(await page.locator(item_selector).first.inner_text()).strip()
        await next_button.click()
        try:
            await page.wait_for_function(
                "([selector, oldText]) => { const el=document.querySelector(selector); return el && el.innerText.trim() !== oldText; }",
                arg=[item_selector,old_first],timeout=15000
            )
        except Exception:
            await page.wait_for_timeout(1200)
async def retry_failed_items(job:int,page,cfg:dict):
    """Retry exact saved requests, including failures beyond the first pages."""
    failures=db.unresolved_failures()
    works={work['item_key']:work for work in db.work_items('sync',('failed',))}
    wanted={row['url'] for row in failures if row['stage'] in {'api_download','download','mock'}}
    # Older releases did not retain a retry payload. Recover it from the
    # downloaded API pages, without re-enumerating the remote list.
    available={work['payload']['item']['detail_url'] for work in works.values()}
    missing=wanted-available
    if missing:
        for path in DIRS['raw_json'].glob('*.json'):
            try:
                result=json.loads(path.read_text(encoding='utf-8'))
                for row in extract_rows(result):
                    item=normalize_notice(row,cfg)
                    if item['detail_url'] in missing:
                        raw=item.pop('raw_api');queue_item(item,'api',raw)
                        missing.remove(item['detail_url'])
            except (OSError,ValueError,PortalApiError):continue
        for url in missing:
            if not is_allowed_url(url,cfg):continue
            # Plain detail links are directly retryable. API failures without
            # cached bodies are kept unresolved rather than guessed as pages.
            if any(row['url']==url and row['stage']=='download' for row in failures):
                queue_item({'title':'来源文章','detail_url':url},'page')
        works.update({work['item_key']:work for work in db.work_items('sync',('pending',)) if work['item_key'] in wanted})
    recognition_ids=set()
    recognition_failures=set()
    for failure in failures:
        if failure['stage']=='auto_recognition' and failure['url'].startswith('attachment:'):
            try:article_id=db.article_for_attachment(int(failure['url'].split(':')[1]))
            except ValueError:article_id=None
            if article_id:recognition_ids.add(article_id);recognition_failures.add(failure['id'])
    STATE['total']=len(works)+len(recognition_ids)
    downloaded_ids=set()
    for work in works.values():
        matching=[row for row in failures if row['url'] in {work['item_key'],work['payload']['item']['detail_url']} and row['stage'] in {'api_download','download','mock','api_mapping'}]
        article_id=await download_work(work,job,page,cfg,track_checkpoint=False)
        if article_id:downloaded_ids.add(article_id)
        outstanding={row['id'] for row in db.unresolved_failures()}
        for failure in matching:
            db.retry_failure(failure['id'], '重试仍未成功' if failure['id'] in outstanding else None)
    process_ids=recognition_ids|downloaded_ids
    STATE['total']+=len(downloaded_ids-recognition_ids)
    if process_ids:
        from . import process
        from ..models import ProcessRequest
        # Run in this task so retry progress includes actual OCR completion.
        await process.run(ProcessRequest(article_ids=sorted(process_ids),build_index=False))
        outstanding={row['id'] for row in db.unresolved_failures()}
        for failure in failures:
            if failure['id'] in recognition_failures:
                db.retry_failure(failure['id'],'重试仍未成功' if failure['id'] in outstanding else None)
        STATE['current']+=len(process_ids)
        STATE['failed']+=process.STATE.get('failed',0)
    left=db.unresolved_failures()
    STATE['message']=f"精确重试完成；仍有 {len(left)} 个失败项" if left else '精确重试完成，失败项已全部恢复'

async def run(req:SyncRequest):
    STATE.update(status="running",current=0,total=0,success=0,failed=0,message="开始同步")
    saved_checkpoint=db.checkpoint('sync')
    if req.mode=='resume' and saved_checkpoint:
        req=SyncRequest(**saved_checkpoint['request'])
        STATE.update(saved_checkpoint.get('progress',{}));STATE['status']='running'
    elif req.mode=='full' and not saved_checkpoint:
        db.save_checkpoint('sync',{'request':req.model_dump(),'progress':dict(STATE)})
    job=db.create_job(req.mode)
    try:
        await (mock_sync(req,job) if req.mode=="mock" else portal_sync(req,job))
        final_message=STATE.get("message","")
        if not final_message or final_message=="开始同步":final_message="同步完成"
        elif "完成" not in final_message:final_message+= "；同步完成"
        STATE.update(status="completed",message=final_message);db.finish_job(job,"completed",STATE["current"],STATE["success"],STATE["failed"])
        if req.mode=="full":
            from .process import start as start_processing
            from ..models import ProcessRequest
            from ..processing.field_extractor import PIPELINE_VERSION
            await start_processing(ProcessRequest(all_local=db.metadata('pipeline_version')!=PIPELINE_VERSION,build_index=False))
            db.set_metadata('initial_sync_complete','1')
            db.save_checkpoint('sync',None)
            STATE["message"] += "；附件与记录识别已在后台启动"
    except Exception as e:
        STATE.update(status="failed",message=f"同步暂停：{type(e).__name__}: {e}");db.finish_job(job,"failed",STATE["current"],STATE["success"],STATE["failed"],STATE["message"])
        if req.mode!='retry':checkpoint_progress()
@router.post("/start")
async def start(req:SyncRequest):
    global task
    if task and not task.done():return STATE
    from . import process
    if process.task and not process.task.done():raise HTTPException(409,'自动识别正在运行，请完成后更新数据')
    if req.mode=='resume' and not db.checkpoint('sync'):raise HTTPException(400,'没有待继续的采集任务')
    if db.checkpoint('sync'):
        if req.mode=='full':req=SyncRequest(mode='resume',max_pages=req.max_pages)
        elif req.mode not in {'resume','retry'}:raise HTTPException(409,'上次采集尚未完成，请先继续采集')
    STATE.update(status='running',current=0,total=0,message='正在准备拉取数据')
    task=asyncio.create_task(run(req));return STATE

_ensured=False
@router.post('/ensure')
async def ensure():
    """Run once after authentication; fresh installations fetch, upgrades reprocess."""
    global _ensured
    if _ensured:return {'started':False}
    ok,_=await browser_session.is_logged_in()
    if not ok:raise HTTPException(401,'需要先完成学校认证')
    from . import process
    from ..processing.field_extractor import PIPELINE_VERSION
    if (task and not task.done()) or (process.task and not process.task.done()):return {'started':False}
    _ensured=True
    stats=db.stats()
    if db.checkpoint('sync'):
        await start(SyncRequest(mode='resume',max_pages=1000))
        return {'started':True,'stage':'sync'}
    if db.checkpoint('process'):
        from ..models import ProcessRequest
        await process.start(ProcessRequest(build_index=False))
        return {'started':True,'stage':'process'}
    if db.work_items('sync',('failed',)):
        await start(SyncRequest(mode='retry',max_pages=1000))
        return {'started':True,'stage':'sync'}
    if db.work_items('process',('pending',)):
        from ..models import ProcessRequest
        await process.start(ProcessRequest(build_index=False))
        return {'started':True,'stage':'process'}
    if stats['articles']==0:
        await start(SyncRequest(mode='full',max_pages=1000))
        return {'started':True,'stage':'sync'}
    if db.metadata('pipeline_version')!=PIPELINE_VERSION:
        from ..models import ProcessRequest
        await process.start(ProcessRequest(all_local=True,build_index=False))
        return {'started':True,'stage':'process'}
    return {'started':False}
@router.get("/status")
async def status():
    saved=db.checkpoint('sync')
    if saved and STATE['status']=='idle':
        return {**STATE,**saved.get('progress',{}),'status':'paused','message':'上次采集尚未完成，登录后会自动继续','resume_available':True}
    return {**STATE,'resume_available':bool(saved)}
@router.post("/retry")
async def retry():
    return await start(SyncRequest(mode="retry",max_pages=1000))
