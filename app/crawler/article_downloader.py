from __future__ import annotations
import hashlib
from pathlib import Path
from urllib.parse import unquote, urlparse
from ..settings import DIRS,safe_filename,is_allowed_url
from ..processing.html_parser import clean_html,extract_attachments
from .browser_session import browser_session

def digest(data: bytes)->str:return hashlib.sha256(data).hexdigest()
async def save_article(page, item:dict, config:dict, navigate:bool=True) -> tuple[dict,list[dict]]:
    if not is_allowed_url(item["detail_url"],config):raise ValueError("详情链接不在允许域名内")
    if navigate:
        await page.goto(item["detail_url"],wait_until="domcontentloaded")
        selector=config.get("detail_body_selector","")
        if selector and not selector.startswith("TODO"):
            try:await page.locator(selector).first.wait_for(state="attached",timeout=15000)
            except Exception:pass
        await page.wait_for_timeout(400)
    html=await page.content(); aid=digest(item["detail_url"].encode())[:16]
    raw=DIRS["raw_html"]/(aid+".html"); raw.write_text(html,encoding="utf-8")
    text=clean_html(html,config.get("detail_body_selector")); txt=DIRS["article_text"]/(aid+".txt"); txt.write_text(text,encoding="utf-8")
    item.update(raw_html_path=str(raw),text_path=str(txt),content_hash=digest(text.encode()),download_status="done")
    attachments=[]
    for link in extract_attachments(html,item["detail_url"],config.get("attachment_selector","")):
        if not is_allowed_url(link["url"],config):
            attachments.append({"name":link["name"],"file_path":link["url"],"file_type":"external_link","file_hash":digest(link["url"].encode()),"is_external":True});continue
        status,headers,content=await browser_session.attachment_content(page,link["url"]); ctype=headers.get("content-type","")
        if status>=400 or "text/html" in ctype or b"<html" in content[:500].lower():raise ValueError("附件返回了错误页或登录页")
        name=safe_filename(link["name"]); path=DIRS["attachments"]/(aid+"_"+name);path.write_bytes(content)
        attachments.append({"name":name,"file_path":str(path),"file_type":path.suffix.lower(),"file_hash":digest(content)})
    return item,attachments

async def save_api_article(page, item:dict, row:dict, config:dict) -> tuple[dict,list[dict]]:
    """直接保存列表接口返回的正文，不再逐条打开通知详情页。"""
    content=row.get("notice_content")
    if not isinstance(content,str) or not content.strip():
        raise ValueError("接口记录中没有 notice_content 正文")

    aid=digest(item["detail_url"].encode())[:16]
    html=("<!doctype html><html><head><meta charset='utf-8'></head><body>"
          f"<main class='api-notice-content'>{content}</main></body></html>")
    raw=DIRS["raw_html"]/(aid+".html");raw.write_text(html,encoding="utf-8")
    text=clean_html(html,".api-notice-content")
    txt=DIRS["article_text"]/(aid+".txt");txt.write_text(text,encoding="utf-8")
    item.update(raw_html_path=str(raw),text_path=str(txt),content_hash=digest(text.encode()),download_status="done")

    attachments=[];seen=set()
    for link in extract_attachments(html,item["detail_url"],".api-notice-content a[href], .api-notice-content img[src]"):
        url=link["url"]
        if url in seen or url.startswith(("data:","javascript:")):continue
        seen.add(url)
        if not is_allowed_url(url,config):
            attachments.append({"name":link["name"],"file_path":url,"file_type":"external_link","file_hash":digest(url.encode()),"is_external":True})
            continue
        status,headers,content_bytes=await browser_session.attachment_content(page,url)
        ctype=headers.get("content-type","")
        if status>=400 or "text/html" in ctype or b"<html" in content_bytes[:500].lower():
            raise ValueError(f"附件下载失败：HTTP {status} {url}")
        url_name=unquote(Path(urlparse(url).path).name)
        name=safe_filename(link["name"] or url_name or "attachment")
        if "." not in name and url_name:name=safe_filename(url_name)
        path=DIRS["attachments"]/(aid+"_"+name);path.write_bytes(content_bytes)
        attachments.append({"name":name,"file_path":str(path),"file_type":path.suffix.lower(),"file_hash":digest(content_bytes)})
    return item,attachments
