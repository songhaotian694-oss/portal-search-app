from __future__ import annotations
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def clean_html(html: str, body_selector: str | None = None) -> str:
    soup=BeautifulSoup(html,"html.parser")
    for node in soup(["script","style","nav","footer","header","button","noscript"]): node.decompose()
    root=soup.select_one(body_selector) if body_selector and not body_selector.startswith("TODO") else soup.body or soup
    return "\n".join(line.strip() for line in root.get_text("\n").splitlines() if line.strip())

def parse_list_page(html: str, base_url: str, config: dict) -> list[dict]:
    soup=BeautifulSoup(html,"html.parser"); result=[]
    item_sel=config.get("list_item_selector","")
    if not item_sel or item_sel.startswith("TODO"): return result
    for item in soup.select(item_sel):
        def txt(key):
            sel=config.get(key,""); el=item.select_one(sel) if sel and not sel.startswith("TODO") else None
            return el.get_text(" ",strip=True) if el else ""
        link_sel=config.get("detail_link_selector",""); link=item.select_one(link_sel) if link_sel and not link_sel.startswith("TODO") else item.select_one("a[href]")
        if not link or not link.get("href"): continue
        href=urljoin(base_url,link["href"])
        result.append({"portal_id":item.get("data-id") or link.get("data-id"),"title":txt("title_selector") or link.get_text(" ",strip=True),"published_at":txt("date_selector"),"detail_url":href,"category":"就业信息"})
    return result

def has_next_page(html: str, config: dict) -> bool:
    sel=config.get("next_button_selector","")
    if not sel or sel.startswith("TODO"):return False
    el=BeautifulSoup(html,"html.parser").select_one(sel)
    return bool(el and not el.has_attr("disabled") and "disabled" not in (el.get("class") or []))

def extract_attachments(html: str, base_url: str, selector: str) -> list[dict]:
    if not selector or selector.startswith("TODO"): return []
    soup=BeautifulSoup(html,"html.parser"); out=[]
    for el in soup.select(selector):
        href=el.get("href") or el.get("data-url") or el.get("src")
        if href:
            name=el.get_text(" ",strip=True) or el.get("alt") or href.rsplit("/",1)[-1]
            out.append({"url":urljoin(base_url,href),"name":name})
    return out
