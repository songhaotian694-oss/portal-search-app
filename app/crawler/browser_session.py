from __future__ import annotations
import asyncio
import json
import logging
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from ..settings import DATA_DIR, load_config
from ..desktop_login import desktop_login
from .auth_store import AuthStore

logger = logging.getLogger(__name__)


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
    """User-entered authentication, with a native view and a retained crawler page."""

    def __init__(self, store: AuthStore | None = None, desktop=None):
        self.playwright = self.browser = self.context = self.page = None
        self.login_hwnd = 0
        self.store = store or AuthStore()
        self.desktop = desktop or desktop_login
        self._lock = asyncio.Lock()
        self._monitor = None
        self._restore_attempted = False
        self._restore_retry_at = 0.0
        self._authenticated = False
        self._owns_browser = False
        self._headless = False
        self._login_open = False
        self.message = ""

    def _status(self, ok: bool = False, url: str = "") -> dict:
        return {
            "started": self.page is not None and not self.page.is_closed(),
            "logged_in": ok,
            "url": url,
            "remember_login": self.store.remembers(),
            "embedded": self.desktop.available,
            "login_open": self._login_open,
            "message": self.message,
        }

    async def _create_session(self, visible: bool) -> None:
        from playwright.async_api import async_playwright
        from .portal_api import install_api_capture

        self.playwright = await async_playwright().start()
        self._owns_browser = not self.desktop.available
        self._headless = not visible
        try:
            if self.desktop.available:
                marker = await asyncio.to_thread(self.desktop.ensure)
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    f"http://127.0.0.1:{self.desktop.debug_port}", timeout=15000
                )
                for _ in range(50):
                    self.page = next((page for context in self.browser.contexts for page in context.pages
                                      if page.url == marker), None)
                    if self.page:
                        break
                    await asyncio.sleep(.1)
                if self.page is None:
                    raise RuntimeError("无法连接软件内的认证页面，请重启软件。")
                self.context = self.page.context
            else:
                candidates = [("Edge", {"channel": "msedge"}), ("Chrome", {"channel": "chrome"})]
                chromium = _installed_chromium()
                if chromium:
                    candidates.append(("Chromium", {"executable_path": str(chromium)}))
                failures = []
                for label, options in candidates:
                    try:
                        self.browser = await self.playwright.chromium.launch(headless=not visible, **options)
                        break
                    except Exception as exc:
                        failures.append(f"{label}: {str(exc).splitlines()[0]}")
                if self.browser is None:
                    raise RuntimeError("无法打开认证浏览器，请检查 Edge 或 Chrome。" + "；".join(failures))
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
            install_api_capture(self.context)
        except Exception:
            await self._disconnect()
            raise

    async def _disconnect(self) -> None:
        # Closing a CDP-attached WebView2 browser could close the app's main
        # page too. Only close browsers launched and owned by this session.
        if self.browser and self._owns_browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.playwright = self.browser = self.context = self.page = None
        self._authenticated = False

    async def _apply_saved_state(self, state: dict) -> None:
        storage = state["storage"]
        if self.desktop.available:
            # Each private WebView2 control has its own cookie partition; the
            # browser's default context cookie API refers to the main app view.
            connection = await self.context.new_cdp_session(self.page)
            try:
                await connection.send("Network.setCookies", {"cookies": storage.get("cookies", [])})
            finally:
                await connection.detach()
        else:
            await self.context.add_cookies(storage.get("cookies", []))
        origins = {item["origin"]: item.get("localStorage", []) for item in storage.get("origins", [])}
        values = json.dumps({"local": origins, "session": state.get("session", {})})
        # Restore each origin only once per tab, so subsequent logout or token
        # refresh cannot be overwritten by an old saved token on navigation.
        await self.page.add_init_script("""(() => {
            const state = STATE;
            if (sessionStorage.getItem('__zhixu_restored__')) return;
            const origin = location.origin;
            for (const item of state.local[origin] || []) localStorage.setItem(item.name, item.value);
            for (const [key, value] of Object.entries(state.session[origin] || {})) sessionStorage.setItem(key, value);
            sessionStorage.setItem('__zhixu_restored__', '1');
        })();""".replace("STATE", values))

    async def native_cookies(self, page=None) -> list[dict]:
        connection = await self.context.new_cdp_session(page or self.page)
        try:
            cookies = (await connection.send("Network.getAllCookies"))["cookies"]
        finally:
            await connection.detach()
        keys = {"name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite", "partitionKey"}
        result = [{key: value for key, value in cookie.items() if key in keys} for cookie in cookies]
        for cookie in result:
            cookie.setdefault("sameSite", "Lax")
        return result

    async def attachment_content(self, page, url: str) -> tuple[int, dict, bytes]:
        if self.desktop.available and page is self.page:
            # APIRequestContext is separate from WebView2's private partition.
            # Seed a short-lived request client from this target's current
            # cookies, so protected and cross-origin allowed attachments work.
            cookies = await self.native_cookies(page)
            request_cookies = [{key: value for key, value in cookie.items() if key != "partitionKey"} for cookie in cookies]
            client = await self.playwright.request.new_context(storage_state={"cookies": request_cookies, "origins": []})
            try:
                response = await client.get(url)
                return response.status, response.headers, await response.body()
            finally:
                await client.dispose()
        response = await page.request.get(url)
        return response.status, response.headers, await response.body()

    async def _snapshot(self) -> dict:
        if self.desktop.available:
            # WebView2 owns its native targets and cannot create Playwright's
            # temporary storage_state page. Read storage on our existing page.
            local = await self.page.evaluate("""() => Object.entries(localStorage).map(
                ([name, value]) => ({name, value}))""")
            parsed = urlparse(self.page.url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            storage = {"cookies": await self.native_cookies(),
                       "origins": [{"origin": origin, "localStorage": local}]}
        else:
            storage = await self.context.storage_state()
        config = load_config()
        login_host, target_host = _login_and_target_hosts(config.get("portal_url", ""))
        allowed = [login_host, target_host, *config.get("allowed_domains", [])]

        def allowed_host(host):
            return any(domain and not domain.startswith("TODO") and
                       (host == domain or host.endswith("." + domain)) for domain in allowed)

        # Exclude the local React app and any unrelated WebView2 storage.
        storage["cookies"] = [cookie for cookie in storage.get("cookies", [])
                              if allowed_host(cookie["domain"].lstrip("."))]
        storage["origins"] = [item for item in storage.get("origins", []) if allowed_host(_host(item["origin"]))]
        session = await self.page.evaluate("""() => Object.fromEntries(
            Object.entries(sessionStorage).filter(([key]) => key !== '__zhixu_restored__'))""")
        parsed = urlparse(self.page.url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return {"storage": storage, "session": {origin: session}}

    async def _wait_for_restored_login(self, timeout: float = 6.0) -> bool:
        """SSO and portal JavaScript may redirect after DOMContentLoaded."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        stable_url = ""
        stable_since = loop.time()
        while True:
            ok, url = await self._detect_logged_in()
            now = loop.time()
            if not ok or url != stable_url:
                stable_url = url if ok else ""
                stable_since = now
            elif now - stable_since >= 1.0:
                return True
            if now >= deadline:
                return False
            await asyncio.sleep(min(.25, deadline - now))

    async def _restore_once(self) -> None:
        if self._restore_attempted or asyncio.get_running_loop().time() < self._restore_retry_at:
            return
        self._restore_attempted = True
        state = self.store.load()
        if not state:
            return
        try:
            await self._create_session(visible=False)
            await self._apply_saved_state(state)
            config = load_config()
            login_url = config["portal_url"]
            login_host, target_host = _login_and_target_hosts(login_url)
            entry = config.get("employment_entry", "")
            urls = []
            # The portal session can outlive the school's SSO session. Going
            # straight to CAS would require a new login despite valid portal
            # cookies/storage, so try its configured entry before SSO.
            if (urlparse(entry).scheme in {"http", "https"} and _host(entry) == target_host
                    and target_host != login_host):
                urls.append(entry)
            if login_url not in urls:
                urls.append(login_url)
            for url in urls:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if await self._wait_for_restored_login():
                    await self._complete_login()
                    self.message = "已恢复本机登录状态。"
                    return
            # A redirect/loading page is not proof of expiry. Keep the file
            # until a successful login replaces it or retention is disabled.
            self.message = "保留的登录状态未能通过验证，请重新登录。"
        except Exception as exc:
            # Network/WebView startup failure must leave normal manual login
            # available, and must not discard a potentially valid saved session.
            self.message = "暂时无法恢复登录状态，请在软件内重新登录。" if self.desktop.available else "暂时无法恢复登录状态，请重新登录。"
            self._restore_attempted = False
            self._restore_retry_at = asyncio.get_running_loop().time() + 10
            logger.warning("Retained authentication restore failed (%s).", type(exc).__name__)
        if self.desktop.available:
            await asyncio.to_thread(self.desktop.dispose)
        await self._disconnect()

    async def start(self, remember_login: bool | None = None) -> dict:
        async with self._lock:
            if remember_login is not None:
                self.store.set_remember(remember_login)
            self._restore_attempted = True
            self.message = ""
            if self.page and not self.page.is_closed():
                ok, url = await self._detect_logged_in()
                if ok:
                    await self._complete_login()
                    return self._status(True, url)
                if self._headless and not self.desktop.available:
                    await self._disconnect()
            previous = set(_browser_windows()) if not self.desktop.available else set()
            if not self.page or self.page.is_closed():
                await self._disconnect()
                await self._create_session(visible=True)
            try:
                if self.desktop.available:
                    await asyncio.to_thread(self.desktop.show)
                await self.page.goto(load_config()["portal_url"], wait_until="domcontentloaded", timeout=20000)
                if not self.desktop.available:
                    await self.page.bring_to_front()
                    self.login_hwnd = _show_browser_window(previous, await self.page.title(), self.login_hwnd)
                    if os.name == "nt" and not self.login_hwnd:
                        raise RuntimeError("认证浏览器已启动，但窗口无法显示。请通过桌面软件启动。")
                self._login_open = True
                self._authenticated = False
                self.message = "请完成学校统一认证，成功后会自动返回首页。"
                if self._monitor is None or self._monitor.done():
                    self._monitor = asyncio.create_task(self._watch_login())
                return self._status(False, self.page.url)
            except Exception:
                if self.desktop.available:
                    await asyncio.to_thread(self.desktop.hide)
                self._login_open = False
                raise

    async def _detect_logged_in(self) -> tuple[bool, str]:
        if not self.page or self.page.is_closed():
            return False, "尚未打开认证页面"
        try:
            config = load_config()
            login_host, target_host = _login_and_target_hosts(config.get("portal_url", ""))
            if self._owns_browser:
                pages = [page for page in self.context.pages if not page.is_closed()]
                target = next((page for page in reversed(pages) if target_host and _host(page.url) == target_host), None)
                if target:
                    self.page = target
            # Native WebView2's new-window handler keeps SSO in our one view;
            # never select the application's local main page from CDP contexts.
            url = self.page.url
            current_host = _host(url)
            if not current_host or (current_host == login_host and current_host != target_host):
                return False, url
            allowed = target_host and current_host == target_host
            allowed = allowed or any(domain and not domain.startswith("TODO") and
                                     (current_host == domain or current_host.endswith("." + domain))
                                     for domain in config.get("allowed_domains", []))
            if not allowed:
                return False, url
            await self.page.wait_for_load_state("domcontentloaded", timeout=2000)
            if await self.page.locator('input[type="password"]:visible').count():
                return False, url
            if not await self.page.locator("body").count():
                return False, url
            return True, url
        except Exception:
            return False, "认证页面当前不可用，请重新登录。"

    async def _complete_login(self) -> None:
        if not self._authenticated:
            self._authenticated = True
            if self.store.remembers():
                try:
                    self.store.save(await self._snapshot())
                    self.message = "登录成功，已保留本机登录状态。"
                except Exception as exc:
                    self.message = "登录成功，但未能保存登录状态，下次启动需要重新登录。"
                    logger.warning("Retained authentication save failed (%s).", type(exc).__name__)
            else:
                self.message = "登录成功，本次会话关闭后不保留登录状态。"
        if self._login_open or (self.desktop.available and self.desktop.visible):
            if self.desktop.available:
                await asyncio.to_thread(self.desktop.hide)
            else:
                # Browser-only fallback: remove its visible native window while
                # the owned browser continues serving the background crawler.
                _release_browser_window(self.login_hwnd)
                if os.name == "nt" and self.login_hwnd:
                    import ctypes
                    from ctypes import wintypes
                    ctypes.windll.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
                    ctypes.windll.user32.ShowWindow(self.login_hwnd, 0)
            self._login_open = False

    async def get_status(self) -> dict:
        async with self._lock:
            await self._restore_once()
            if self.desktop.available and self.desktop.cancelled and self._login_open:
                self._login_open = False
                self.message = "已返回软件，可重新开始登录。"
            ok, url = await self._detect_logged_in()
            if ok:
                await self._complete_login()
            else:
                self._authenticated = False
            return self._status(ok, url)

    async def _watch_login(self) -> None:
        while self._login_open:
            try:
                status = await self.get_status()
                if status["logged_in"] or not status["login_open"]:
                    return
            except Exception:
                self.message = "认证页面暂时不可用，请返回软件后重试。"
            await asyncio.sleep(1)

    async def is_logged_in(self) -> tuple[bool, str]:
        status = await self.get_status()
        return status["logged_in"], status["url"]

    async def confirm(self) -> dict:
        return await self.get_status()

    async def set_remember(self, value: bool) -> dict:
        async with self._lock:
            self.store.set_remember(value)
            if value and self._authenticated and self.context:
                self.store.save(await self._snapshot())
            return {"remember_login": value}

    async def cancel(self) -> dict:
        async with self._lock:
            if self.desktop.available:
                await asyncio.to_thread(self.desktop.cancel)
            self._login_open = False
            self.message = "已取消登录，可随时重新开始。"
            if not self._authenticated:
                if self.desktop.available:
                    await asyncio.to_thread(self.desktop.dispose)
                await self._disconnect()
            return self._status(self._authenticated, self.page.url if self.page else "")

    async def close(self) -> None:
        self._login_open = False
        if self._monitor and self._monitor is not asyncio.current_task():
            self._monitor.cancel()
            try:
                await self._monitor
            except asyncio.CancelledError:
                pass
        async with self._lock:
            if self._authenticated and self.context and self.store.remembers():
                try:
                    self.store.save(await self._snapshot())
                except Exception as exc:
                    logger.warning("Retained authentication final save failed (%s).", type(exc).__name__)
            await self._disconnect()
            self.login_hwnd = 0


browser_session = BrowserSession()
