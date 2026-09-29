from __future__ import annotations
from fastapi import APIRouter,HTTPException
from bs4 import BeautifulSoup
from ..settings import load_config,save_config,DIRS
from ..models import SettingsUpdate
from ..crawler.browser_session import browser_session
router=APIRouter(prefix="/api/settings",tags=["设置"])
KEYS=["list_item_selector","title_selector","date_selector","detail_link_selector","next_button_selector","detail_body_selector","attachment_selector"]
@router.get("")
async def get():return load_config()
@router.put("")
async def put(req:SettingsUpdate):return save_config({**load_config(),**req.values})
@router.post("/test-selectors")
async def test():
    if not browser_session.page:raise HTTPException(400,"请先打开浏览器并进入就业信息栏目")
    html=await browser_session.page.content();out=DIRS["diagnostics"] / "current_page_sanitized.html"
    soup=BeautifulSoup(html,"html.parser")
    for n in soup.select("input[type=password],input[name*=password i]"):n["value"]="[已移除]"
    for n in soup.select("script"):n.decompose()
    out.write_text(str(soup),encoding="utf-8")
    result={}
    for key in KEYS:
        selector=load_config().get(key,"")
        if not selector or selector.startswith("TODO"):result[key]={"count":0,"error":"需要填写真实 CSS 选择器","sample":[]};continue
        try:
            nodes=soup.select(selector);result[key]={"count":len(nodes),"sample":[n.get_text(" ",strip=True)[:80] for n in nodes[:3]]}
        except Exception as e:result[key]={"count":0,"error":f"选择器语法无效：{e}","sample":[]}
    return {"saved_path":str(out),"results":result}
