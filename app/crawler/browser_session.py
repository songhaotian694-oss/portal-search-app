from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from ..settings import DATA_DIR, load_config


def _installed_chromium() -> Path | None:
    """查找 Playwright 已下载的可见版 Chromium。"""
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    browser_root = local_app_data / "ms-playwright"
    if not browser_root.exists():
        return None

    # 新版目录为 chrome-win64，旧版可能为 chrome-win。
    candidates = []
    for pattern in (
        "chromium-*/chrome-win64/chrome.exe",
        "chromium-*/chrome-win/chrome.exe",
    ):
        candidates.extend(browser_root.glob(pattern))
    return next((path for path in sorted(candidates, reverse=True) if path.is_file()), None)


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _login_and_target_hosts(portal_url: str) -> tuple[str, str]:
    """从统一认证地址取得认证域名和认证成功后的目标域名。"""
    parsed = urlparse(portal_url)
    login_host = (parsed.hostname or "").lower()
    service = parse_qs(parsed.query).get("service", [""])[0]
    target_host = _host(unquote(service))
    return login_host, target_host


class BrowserSession:
    """只保留用户手工登录后的浏览器上下文，不接触账号、密码或验证码。"""
    def __init__(self): self.playwright=None; self.browser=None; self.context=None; self.page=None; self.state_path=DATA_DIR/"playwright_state.json"
    async def start(self) -> str:
        if self.page and not self.page.is_closed():return self.page.url
        if self.page:await self.close()
        from playwright.async_api import async_playwright
        self.playwright=await async_playwright().start()
        try:
            chromium = _installed_chromium()
            if chromium:
                self.browser = await self.playwright.chromium.launch(
                    headless=False, executable_path=str(chromium)
                )
            else:
                # Windows 通常已有 Edge，未下载 Chromium 时先尝试使用它。
                try:
                    self.browser = await self.playwright.chromium.launch(
                        headless=False, channel="msedge"
                    )
                except Exception as edge_error:
                    raise RuntimeError(
                        "未找到可用浏览器。请关闭软件后双击 install_browser.bat，"
                        "安装完成后重新启动。"
                    ) from edge_error

            context_options = {}
            if self.state_path.is_file():
                context_options["storage_state"] = str(self.state_path)
            self.context=await self.browser.new_context(**context_options)
            from .portal_api import install_api_capture
            install_api_capture(self.context)
            self.page=await self.context.new_page(); url=load_config()["portal_url"]
            if url.startswith("http"):await self.page.goto(url,wait_until="domcontentloaded")
            return self.page.url
        except Exception:
            # 失败时清理状态，安装浏览器后无需重启后端即可再次点击。
            if self.browser:
                await self.browser.close()
            await self.playwright.stop()
            self.playwright=self.browser=self.context=self.page=None
            raise
    async def is_logged_in(self) -> tuple[bool,str]:
        if not self.page:return False,"尚未打开登录浏览器"
        try:
            config = load_config()
            login_host, target_host = _login_and_target_hosts(config.get("portal_url", ""))

            # 某些统一认证流程会把门户开在新标签页，优先跟踪该页面。
            pages = [page for page in (self.context.pages if self.context else []) if not page.is_closed()]
            target_page = next((page for page in reversed(pages) if _host(page.url) == target_host), None)
            if target_page:
                self.page = target_page
            elif pages:
                self.page = pages[-1]
            else:
                return False,"登录浏览器已关闭，请重新点击“登录门户”"

            url = self.page.url
            current_host = _host(url)

            # 统一认证成功后会从 ca.muc.edu.cn 跳转到 service 指定的门户域名。
            # 不能用“登录”两个字判断，因为门户首页常有“退出登录”等文字。
            if target_host and current_host == target_host:
                return True,url
            if login_host and current_host == login_host:
                return False,url
            if current_host and any(
                current_host == domain or current_host.endswith("." + domain)
                for domain in config.get("allowed_domains", [])
                if domain and not domain.startswith("TODO")
            ):
                password_boxes = self.page.locator('input[type="password"]:visible')
                return await password_boxes.count() == 0,url
            return False,url
        except Exception:
            return False,"登录页面当前不可用，请重新点击“登录门户”"
    async def confirm(self) -> tuple[bool,str]:
        ok,url=await self.is_logged_in()
        if ok and self.context: await self.context.storage_state(path=str(self.state_path))
        return ok,url
    async def close(self) -> None:
        if self.browser:await self.browser.close()
        if self.playwright:await self.playwright.stop()
        self.playwright=self.browser=self.context=self.page=None
browser_session=BrowserSession()
