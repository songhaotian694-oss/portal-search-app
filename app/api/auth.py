from fastapi import APIRouter, HTTPException
from ..crawler.browser_session import browser_session
router=APIRouter(prefix="/api/auth",tags=["认证"])
@router.post("/start")
async def start():
    try:return {"url":await browser_session.start(),"message":"已打开可见浏览器，请自行完成认证；软件不会读取账号、密码或验证码。"}
    except Exception as e:raise HTTPException(500,f"无法启动 Chromium：{type(e).__name__}: {e}")
@router.get("/status")
async def status():
    ok,url=await browser_session.is_logged_in();return {"started":browser_session.page is not None,"logged_in":ok,"url":url}
@router.post("/confirm")
async def confirm():
    ok,url=await browser_session.confirm();return {"logged_in":ok,"url":url,"message":"登录状态已本地保存（包含敏感 Cookie，请勿分享）。" if ok else "仍检测到登录页，请完成登录后再确认。"}
