from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from ..settings import DATA_DIR, load_config


def _browser_windows() -> dict[int, str]:
    """列出当前桌面上的 Edge/Chrome 顶层窗口。"""
    if os.name != "nt":
        return {}
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    windows: dict[int, str] = {}

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        class_name = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(hwnd, class_name, len(class_name))
        if class_name.value == "Chrome_WidgetWin_1":
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, len(title))
            windows[int(hwnd)] = title.value
        return True

    user32.EnumWindows(visit, 0)
    return windows


def _show_browser_window(previous: set[int], page_title: str, preferred: int = 0) -> int:
    """登录窗口可能在主程序后面，显式恢复并置顶供用户操作。"""
    if os.name != "nt":
        return 0
    import ctypes
    from ctypes import wintypes

    windows = _browser_windows()
    fresh = [hwnd for hwnd in windows if hwnd not in previous]
    matching = [hwnd for hwnd in fresh if page_title and page_title in windows[hwnd]]
    matching += [hwnd for hwnd, title in windows.items() if page_title and page_title in title and hwnd not in matching]
    hwnd = preferred if preferred in windows else (matching or fresh or [0])[0]
    if hwnd:
        user32 = ctypes.windll.user32
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        shown = user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0043)  # HWND_TOPMOST | SWP_SHOWWINDOW
        user32.SetForegroundWindow(hwnd)
        return hwnd if shown else 0
    return 0


def _release_browser_window(hwnd: int) -> None:
    if os.name == "nt" and hwnd:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.SetWindowPos(hwnd, wintypes.HWND(-2), 0, 0, 0, 0, 0x0003)  # HWND_NOTOPMOST


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
    def __init__(self): self.playwright=None; self.browser=None; self.context=None; self.page=None; self.login_hwnd=0; self.state_path=DATA_DIR/"playwright_state.json"
    async def start(self) -> str:
        if self.page and not self.page.is_closed():
            await self.page.bring_to_front()
            self.login_hwnd = _show_browser_window(set(), await self.page.title(), self.login_hwnd)
            if os.name == "nt" and not self.login_hwnd:
                raise RuntimeError("登录浏览器已运行，但窗口无法显示。请关闭登录浏览器后重试。")
            return self.page.url
        if self.page:await self.close()
        previous_windows = set(_browser_windows())
        from playwright.async_api import async_playwright
        self.playwright=await async_playwright().start()
        try:
            # 系统浏览器优先。某些 Windows 机器虽有下载版 Chromium，
            # 但系统会拒绝启动该 exe（Playwright 报 spawn UNKNOWN）。
            candidates = [("Edge", {"channel": "msedge"}), ("Chrome", {"channel": "chrome"})]
            chromium = _installed_chromium()
            if chromium: candidates.append(("Chromium", {"executable_path": str(chromium)}))
            failures = []
            for label, options in candidates:
                try:
                    self.browser = await self.playwright.chromium.launch(
                        headless=False, **options
                    )
                    break
                except Exception as exc:
                    failures.append(f"{label}: {str(exc).splitlines()[0]}")
            if self.browser is None:
                raise RuntimeError(
                    "无法打开登录浏览器。请检查 Edge 或 Chrome，"
                    "也可运行 install_browser.bat 安装 Chromium。"
                    + (" 尝试结果：" + "；".join(failures) if failures else "")
                )

            context_options = {}
            if self.state_path.is_file():
                context_options["storage_state"] = str(self.state_path)
            self.context=await self.browser.new_context(**context_options)
            from .portal_api import install_api_capture
            install_api_capture(self.context)
            self.page=await self.context.new_page(); url=load_config()["portal_url"]
            if url.startswith("http"):await self.page.goto(url,wait_until="domcontentloaded")
            await self.page.bring_to_front()
            self.login_hwnd = _show_browser_window(previous_windows, await self.page.title())
            if os.name == "nt" and not self.login_hwnd:
                raise RuntimeError("登录浏览器已启动，但窗口无法显示。请关闭登录浏览器后重试。")
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
                _release_browser_window(self.login_hwnd)
                return True,url
            if login_host and current_host == login_host:
                return False,url
            if current_host and any(
                current_host == domain or current_host.endswith("." + domain)
                for domain in config.get("allowed_domains", [])
                if domain and not domain.startswith("TODO")
            ):
                password_boxes = self.page.locator('input[type="password"]:visible')
                ok = await password_boxes.count() == 0
                if ok:_release_browser_window(self.login_hwnd)
                return ok,url
            return False,url
        except Exception:
            return False,"登录页面当前不可用，请重新点击“登录门户”"
    async def confirm(self) -> tuple[bool,str]:
        ok,url=await self.is_logged_in()
        if ok and self.context: await self.context.storage_state(path=str(self.state_path))
        return ok,url
    async def close(self) -> None:
        _release_browser_window(self.login_hwnd)
        if self.browser:await self.browser.close()
        if self.playwright:await self.playwright.stop()
        self.playwright=self.browser=self.context=self.page=None
        self.login_hwnd=0
browser_session=BrowserSession()
