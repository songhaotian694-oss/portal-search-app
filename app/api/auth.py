from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..crawler.browser_session import browser_session
router=APIRouter(prefix="/api/auth",tags=["认证"])

class LoginRequest(BaseModel):
    remember_login: bool | None = None

class LoginPreferences(BaseModel):
    remember_login: bool

@router.post("/start")
async def start(request: LoginRequest | None = None):
    try:
        return await browser_session.start(request.remember_login if request else None)
    except Exception as e:
        raise HTTPException(500,f"无法打开认证页面：{str(e).splitlines()[0]}")

@router.get("/status")
async def status():
    return await browser_session.get_status()

@router.post("/confirm")
async def confirm():
    return await browser_session.confirm()

@router.put("/preferences")
async def preferences(request: LoginPreferences):
    try:
        return await browser_session.set_remember(request.remember_login)
    except OSError:
        raise HTTPException(500, "无法保存登录偏好，请检查本机数据目录的写入权限。")

@router.post("/cancel")
async def cancel():
    return await browser_session.cancel()
