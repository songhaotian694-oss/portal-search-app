from __future__ import annotations
import asyncio, hashlib, shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException
from ..database import db
from ..models import SyncRequest
from ..settings import ROOT,DIRS,load_config,is_allowed_url
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
FIX=ROOT/"tests"/"fixtures"
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
    if cfg.get("data_source") in {"api","auto"}:
        try:
            await api_portal_sync(req,job,page,cfg,url)
            return
        except PortalApiError as exc:
            STATE["message"]=f"接口模式不可用，已切换页面模式：{exc}"
    if cfg.get("detail_open_mode") == "click":
        await spa_portal_sync(req,job,page,cfg,url)
        return
    adapter=PortalAdapter(cfg);pages=0
    while url and pages<req.max_pages:
        await page.goto(url,wait_until="domcontentloaded");html=await page.content();items=adapter.parse_list(html,url);STATE["total"]+=len(items)
        for item in items:
            try:
                saved,attachments=await save_article(page,item,cfg);aid,_=db.upsert_article(saved)
                for a in attachments:db.add_attachment(aid,a)
                STATE["success"]+=1
            except Exception as e:db.add_failure(job,item.get("detail_url",""),"download",str(e));STATE["failed"]+=1
            STATE["current"]+=1;await asyncio.sleep(float(cfg.get("page_interval_seconds",1.5)))
        url=adapter.next_url(html,url);pages+=1

async def api_portal_sync(req:SyncRequest,job:int,page,cfg:dict,url:str):
    """复用登录会话直接调用门户JSON接口，页面抓取仅作为后备。"""
    initial_result,template=await capture_first_page(page,url)
    STATE["message"]="已捕获 getNoticeByPage，正在直接读取接口正文（无需逐条打开）"
    keywords=cfg.get("api_keywords") or [""]
    if isinstance(keywords,str):keywords=[keywords]
    seen:set[str]=set()
    for keyword in keywords:
        for page_offset in range(req.max_pages):
            if not keyword and page_offset==0:
                result=initial_result
            else:
                result=await fetch_page(page,template,page_offset,keyword or None)
            save_raw_page(result,keyword,page_offset+1)
            rows=extract_rows(result)
            if not rows:break
            items=[]
            mapping_errors=[]
            for row in rows:
                try:
                    item=normalize_notice(row,cfg)
                    if item["portal_id"] in seen:continue
                    seen.add(item["portal_id"]);items.append(item)
                except PortalApiError as exc:
                    mapping_errors.append(str(exc))
                    db.add_failure(job,url,"api_mapping",str(exc));STATE["failed"]+=1
            if rows and not items:
                raise PortalApiError(mapping_errors[0] if mapping_errors else "接口字段映射失败")
            STATE["total"]+=len(items)
            for item in items:
                try:
                    row=item.pop("raw_api")
                    saved,attachments=await save_api_article(page,item,row,cfg);aid,_=db.upsert_article(saved)
                    for attachment in attachments:db.add_attachment(aid,attachment)
                    make_searchable(aid,saved)
                    STATE["success"]+=1
                except Exception as exc:
                    db.add_failure(job,item.get("detail_url",url),"api_download",str(exc));STATE["failed"]+=1
                STATE["current"]+=1
                await asyncio.sleep(float(cfg.get("page_interval_seconds",1.5)))

async def spa_portal_sync(req:SyncRequest,job:int,page,cfg:dict,url:str):
    """处理标题没有 href、详情和翻页均由 Vue 点击事件驱动的门户页面。"""
    item_selector=cfg["list_item_selector"]
    title_selector=cfg["title_selector"]
    date_selector=cfg["date_selector"]
    next_selector=cfg["next_button_selector"]
    await page.goto(url,wait_until="domcontentloaded")
    await page.locator(item_selector).first.wait_for(state="visible",timeout=15000)
    pages=0
    while pages<req.max_pages:
        list_url=page.url
        rows=page.locator(item_selector)
        row_count=await rows.count()
        STATE["total"]+=row_count
        for index in range(row_count):
            detail_page=None
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
                saved,attachments=await save_article(detail_page,item,cfg,navigate=False);aid,_=db.upsert_article(saved)
                for attachment in attachments:db.add_attachment(aid,attachment)
                STATE["success"]+=1
            except Exception as e:
                db.add_failure(job,list_url,"download",f"第{index+1}条：{e}");STATE["failed"]+=1
            finally:
                if detail_page is not None and detail_page is not page and not detail_page.is_closed():
                    await detail_page.close()
                STATE["current"]+=1
                if page.url != list_url:
                    await page.goto(list_url,wait_until="domcontentloaded")
                    await page.locator(item_selector).first.wait_for(state="visible",timeout=15000)
                await asyncio.sleep(float(cfg.get("page_interval_seconds",1.5)))

        pages+=1
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
async def run(req:SyncRequest):
    STATE.update(status="running",current=0,total=0,success=0,failed=0,message="开始同步")
    job=db.create_job(req.mode)
    try:
        await (mock_sync(req,job) if req.mode=="mock" else portal_sync(req,job))
        final_message=STATE.get("message","")
        if not final_message or final_message=="开始同步":final_message="同步完成"
        elif "完成" not in final_message:final_message+= "；同步完成"
        STATE.update(status="completed",message=final_message);db.finish_job(job,"completed",STATE["current"],STATE["success"],STATE["failed"])
    except Exception as e:
        STATE.update(status="failed",message=f"同步暂停：{type(e).__name__}: {e}");db.finish_job(job,"failed",STATE["current"],STATE["success"],STATE["failed"],STATE["message"])
@router.post("/start")
async def start(req:SyncRequest):
    global task
    if task and not task.done():return STATE
    task=asyncio.create_task(run(req));return STATE
@router.get("/status")
async def status():return STATE
@router.post("/retry")
async def retry():
    # 保留失败记录，重新以用户当前的真实登录状态运行增量任务。
    return await start(SyncRequest(mode="test",max_pages=2))
