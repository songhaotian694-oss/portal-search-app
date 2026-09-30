import asyncio
from copy import deepcopy
import importlib
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.crawler.auth_store import AuthStore
from app.crawler.browser_session import BrowserSession


session_module = importlib.import_module("app.crawler.browser_session")
LOGIN_URL = "https://auth.example.test/login?service=https%3A%2F%2Fportal.example.test%2Fhome"
PORTAL_URL = "https://portal.example.test/home"
SAVED_STATE = {
    "storage": {
        "cookies": [{"name": "test-session", "value": "dummy-value", "domain": "portal.example.test", "path": "/", "sameSite": "Lax"}],
        "origins": [{"origin": "https://portal.example.test", "localStorage": [{"name": "test-key", "value": "dummy-local"}]}],
    },
    "session": {"https://portal.example.test": {"test-session-key": "dummy-session"}},
}


class FakeStore:
    def __init__(self, remember=True, state=None):
        self.remember = remember
        self.state = deepcopy(state)
        self.loads = self.clears = 0
        self.saved = []

    def remembers(self):
        return self.remember

    def load(self):
        self.loads += 1
        return deepcopy(self.state) if self.remember else None

    def save(self, state):
        self.saved.append(deepcopy(state))

    def clear(self):
        self.clears += 1
        self.state = None

    def set_remember(self, value):
        self.remember = value
        if not value:
            self.clear()


class FakeDesktop:
    available = True

    def __init__(self, visible=False):
        self.visible = visible
        self.cancelled = False
        self.hides = self.cancels = self.disposals = 0

    def hide(self):
        self.hides += 1
        self.visible = False

    def cancel(self):
        self.cancels += 1
        self.cancelled = True
        self.hide()

    def dispose(self):
        self.disposals += 1
        self.visible = False


class FakeLocator:
    def __init__(self, count):
        self._count = count

    async def count(self):
        return self._count


class FakePage:
    def __init__(self, url=PORTAL_URL, password_count=0):
        self.url = url
        self.password_count = password_count
        self.context = None
        self.goto = AsyncMock(side_effect=self._navigate)
        self.wait_for_load_state = AsyncMock()
        self.add_init_script = AsyncMock()
        self.evaluate = AsyncMock(side_effect=self._read_storage)
        self.closed = False
        self.navigation_result = PORTAL_URL

    async def _navigate(self, url, **kwargs):
        self.url = self.navigation_result or url

    async def _read_storage(self, script):
        if "Object.entries(localStorage)" in script:
            return deepcopy(SAVED_STATE["storage"]["origins"][0]["localStorage"])
        return {"test-session-key": "dummy-session"}

    def is_closed(self):
        return self.closed

    def locator(self, selector):
        return FakeLocator(self.password_count if "password" in selector else 1)


class FakeCDPConnection:
    def __init__(self, context, page):
        self.context, self.page = context, page
        self.send = AsyncMock(side_effect=self._send)
        self.detach = AsyncMock()

    async def _send(self, method, parameters=None):
        if method == "Network.setCookies":
            self.context.cdp_cookies = deepcopy(parameters["cookies"])
            return {}
        if method == "Network.getAllCookies":
            return {"cookies": deepcopy(self.context.cdp_cookies)}
        raise AssertionError(f"Unexpected CDP command: {method}")


class FakeContext:
    def __init__(self, pages):
        self.pages = pages
        for page in pages:
            page.context = self
        self.add_cookies = AsyncMock()
        self.cookies = AsyncMock(side_effect=lambda: deepcopy(SAVED_STATE["storage"]["cookies"]))
        self.storage_state = AsyncMock(side_effect=lambda: deepcopy(SAVED_STATE["storage"]))
        self.cdp_cookies = deepcopy(SAVED_STATE["storage"]["cookies"])
        self.cdp_connections = []
        self.new_cdp_session = AsyncMock(side_effect=self._connect_target)

    async def _connect_target(self, page):
        connection = FakeCDPConnection(self, page)
        self.cdp_connections.append(connection)
        return connection


@pytest.fixture
def config(monkeypatch):
    value = {"portal_url": LOGIN_URL, "allowed_domains": ["portal.example.test"]}
    monkeypatch.setattr(session_module, "load_config", lambda: value)
    return value


def connected_session(store=None, desktop=None, pages=None):
    store = store or FakeStore()
    desktop = desktop or FakeDesktop(visible=True)
    pages = pages or [FakePage()]
    session = BrowserSession(store=store, desktop=desktop)
    session.context = FakeContext(pages)
    session.page = pages[0]
    session.browser = type("Browser", (), {"close": AsyncMock()})()
    session.playwright = type("Playwright", (), {"stop": AsyncMock()})()
    session._owns_browser = False
    session._restore_attempted = True
    session._login_open = True
    return session


@pytest.mark.skipif(os.name != "nt", reason="Windows protects retained state with DPAPI")
def test_windows_retained_state_is_encrypted_and_reloads_for_same_user(tmp_path):
    store = AuthStore(tmp_path)
    store.set_remember(True)
    store.save(SAVED_STATE)

    data = store.state_path.read_bytes()
    assert data.startswith(b"DPAPI\0")
    assert b"dummy-value" not in data
    assert b"dummy-session" not in data
    assert AuthStore(tmp_path).load() == SAVED_STATE
    assert not store.state_path.with_suffix(".tmp").exists()


def test_turning_retention_off_deletes_encrypted_temporary_and_legacy_state(tmp_path):
    store = AuthStore(tmp_path)
    store.state_path.write_bytes(b"test encrypted data")
    store.state_path.with_suffix(".tmp").write_bytes(b"test unfinished data")
    store.legacy_path.write_text(json.dumps(SAVED_STATE["storage"]), encoding="utf-8")

    store.set_remember(False)

    assert not store.state_path.exists()
    assert not store.state_path.with_suffix(".tmp").exists()
    assert not store.legacy_path.exists()
    assert AuthStore(tmp_path).remembers() is False
    assert AuthStore(tmp_path).load() is None
    store.save(SAVED_STATE)
    assert not store.state_path.exists()


def test_retention_off_does_not_load_a_legacy_file_that_reappears(tmp_path):
    store = AuthStore(tmp_path)
    store.set_remember(False)
    store.legacy_path.write_text(json.dumps(SAVED_STATE["storage"]), encoding="utf-8")
    assert store.load() is None


@pytest.mark.parametrize("data", [
    b"unknown-format", b"JSON\0{", b"JSON\0null", b"JSON\0[]",
    b'JSON\0{"storage": []}', b'JSON\0{"session": {}}', b"DPAPI\0broken-data",
])
def test_corrupt_retained_state_is_ignored(tmp_path, data):
    store = AuthStore(tmp_path)
    store.state_path.write_bytes(data)
    assert store.load() is None


def test_legacy_browser_state_can_be_loaded_without_password_information(tmp_path):
    store = AuthStore(tmp_path)
    store.legacy_path.write_text(json.dumps(SAVED_STATE["storage"]), encoding="utf-8")
    assert store.load() == {"storage": SAVED_STATE["storage"], "session": {}}


def test_status_completes_login_hides_view_and_preserves_crawler_session(config):
    session = connected_session()
    page, context, browser, playwright = session.page, session.context, session.browser, session.playwright

    async def check():
        status = await session.get_status()
        second = await session.get_status()
        assert status["logged_in"] is True
        assert status["started"] is True
        assert status["login_open"] is False
        assert status["embedded"] is True
        assert status["remember_login"] is True
        assert second["logged_in"] is True

    asyncio.run(check())

    assert session.desktop.hides == 1
    assert session.desktop.visible is False
    assert session.page is page and session.context is context
    assert session.browser is browser and session.playwright is playwright
    browser.close.assert_not_awaited()
    playwright.stop.assert_not_awaited()
    assert session.store.saved == [SAVED_STATE]
    context.storage_state.assert_not_awaited()
    context.cookies.assert_not_awaited()
    context.new_cdp_session.assert_awaited_once_with(page)
    context.cdp_connections[0].send.assert_awaited_once_with("Network.getAllCookies")
    context.cdp_connections[0].detach.assert_awaited_once()


def test_retention_off_completes_login_without_reading_or_saving_storage(config):
    session = connected_session(store=FakeStore(remember=False))
    context, page, browser = session.context, session.page, session.browser

    async def check():
        status = await session.get_status()
        assert status["logged_in"] is True
        assert status["remember_login"] is False
        assert status["login_open"] is False
        await session.close()

    asyncio.run(check())

    context.storage_state.assert_not_awaited()
    context.cookies.assert_not_awaited()
    context.new_cdp_session.assert_not_awaited()
    page.evaluate.assert_not_awaited()
    assert session.store.saved == []
    browser.close.assert_not_awaited()


@pytest.mark.parametrize("embedded", [True, False])
def test_saved_state_restores_only_once_and_then_reports_authenticated(config, monkeypatch, embedded):
    store = FakeStore(state=SAVED_STATE)
    session = BrowserSession(store=store, desktop=FakeDesktop())
    session.desktop.available = embedded
    page = FakePage(LOGIN_URL)
    context = FakeContext([page])

    async def create(visible):
        assert visible is False
        session.page, session.context = page, context

    create_session = AsyncMock(side_effect=create)
    monkeypatch.setattr(session, "_create_session", create_session)

    async def check():
        first = await session.get_status()
        second = await session.get_status()
        assert first["logged_in"] and second["logged_in"]
        assert "恢复" in first["message"]

    asyncio.run(check())

    assert store.loads == 1
    assert store.clears == 0
    create_session.assert_awaited_once_with(visible=False)
    page.goto.assert_awaited_once_with(LOGIN_URL, wait_until="domcontentloaded", timeout=15000)
    if embedded:
        context.add_cookies.assert_not_awaited()
        assert context.new_cdp_session.await_count == 2
        assert all(arguments.args == (page,) for arguments in context.new_cdp_session.await_args_list)
        context.cdp_connections[0].send.assert_awaited_once_with(
            "Network.setCookies", {"cookies": SAVED_STATE["storage"]["cookies"]})
        context.cdp_connections[1].send.assert_awaited_once_with("Network.getAllCookies")
        for connection in context.cdp_connections:
            connection.detach.assert_awaited_once()
    else:
        context.add_cookies.assert_awaited_once_with(SAVED_STATE["storage"]["cookies"])
        context.new_cdp_session.assert_not_awaited()
    page.add_init_script.assert_awaited_once()
    assert "__zhixu_restored__" in page.add_init_script.call_args.args[0]


def test_unverified_saved_state_is_kept_and_manual_login_remains_available(config, monkeypatch):
    store = FakeStore(state=SAVED_STATE)
    session = BrowserSession(store=store, desktop=FakeDesktop())
    page = FakePage(LOGIN_URL, password_count=1)
    page.navigation_result = LOGIN_URL
    context = FakeContext([page])
    browser = type("Browser", (), {"close": AsyncMock()})()
    playwright = type("Playwright", (), {"stop": AsyncMock()})()

    async def create(visible):
        session.page, session.context = page, context
        session.browser, session.playwright = browser, playwright

    create_session = AsyncMock(side_effect=create)
    monkeypatch.setattr(session, "_create_session", create_session)

    async def check():
        first = await session.get_status()
        second = await session.get_status()
        assert not first["logged_in"] and not first["started"]
        assert not second["logged_in"]
        assert "未能通过验证" in first["message"]
        assert "重新登录" in first["message"]

    asyncio.run(check())

    assert store.loads == 1 and store.clears == 0
    assert store.state == SAVED_STATE
    assert session.desktop.disposals == 1
    create_session.assert_awaited_once()
    playwright.stop.assert_awaited_once()
    browser.close.assert_not_awaited()


def test_restore_connection_failure_keeps_saved_state_for_a_later_start(config, monkeypatch):
    store = FakeStore(state=SAVED_STATE)
    session = BrowserSession(store=store, desktop=FakeDesktop())
    monkeypatch.setattr(session, "_create_session", AsyncMock(side_effect=RuntimeError("test unavailable")))

    status = asyncio.run(session.get_status())

    assert status["logged_in"] is False
    assert "暂时无法恢复" in status["message"]
    assert store.clears == 0
    assert store.state == SAVED_STATE


@pytest.mark.parametrize("embedded", [True, False])
def test_restore_uses_portal_session_even_when_school_sso_has_expired(config, monkeypatch, embedded):
    entry = "https://portal.example.test/notices"
    config["employment_entry"] = entry
    store = FakeStore(state=SAVED_STATE)
    session = BrowserSession(store=store, desktop=FakeDesktop())
    session.desktop.available = embedded
    page = FakePage(LOGIN_URL)
    context = FakeContext([page])

    async def navigate(url, **kwargs):
        page.url = url
        page.password_count = int(url == LOGIN_URL)

    page.goto.side_effect = navigate

    async def create(visible):
        session.page, session.context = page, context

    monkeypatch.setattr(session, "_create_session", AsyncMock(side_effect=create))
    status = asyncio.run(session.get_status())

    assert status["logged_in"] is True
    assert "恢复" in status["message"]
    page.goto.assert_awaited_once_with(entry, wait_until="domcontentloaded", timeout=15000)
    assert store.clears == 0
    assert store.saved == [SAVED_STATE]


def test_restore_waits_for_school_redirect_after_domcontentloaded(config, monkeypatch):
    store = FakeStore(state=SAVED_STATE)
    session = BrowserSession(store=store, desktop=FakeDesktop())
    page = FakePage(LOGIN_URL, password_count=1)
    page.navigation_result = LOGIN_URL
    context = FakeContext([page])

    async def create(visible):
        session.page, session.context = page, context

    async def check():
        async def finish_sso():
            await asyncio.sleep(.1)
            page.url = PORTAL_URL
            page.password_count = 0
        redirect = asyncio.create_task(finish_sso())
        status = await session.get_status()
        await redirect
        return status

    monkeypatch.setattr(session, "_create_session", AsyncMock(side_effect=create))
    status = asyncio.run(check())
    assert status["logged_in"] is True
    assert store.clears == 0


def test_restore_does_not_accept_portal_that_redirects_back_to_login(config):
    session = connected_session()

    async def check():
        async def redirect_to_login():
            await asyncio.sleep(.1)
            session.page.url = LOGIN_URL
            session.page.password_count = 1
        redirect = asyncio.create_task(redirect_to_login())
        restored = await session._wait_for_restored_login(timeout=.4)
        await redirect
        return restored

    assert asyncio.run(check()) is False


def test_restore_can_retry_after_transient_native_startup_failure(config, monkeypatch):
    store = FakeStore(state=SAVED_STATE)
    session = BrowserSession(store=store, desktop=FakeDesktop())
    page = FakePage()
    context = FakeContext([page])
    attempts = 0

    async def create(visible):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("native view not ready")
        session.page, session.context = page, context

    monkeypatch.setattr(session, "_create_session", AsyncMock(side_effect=create))

    async def check():
        first = await session.get_status()
        assert not first["logged_in"]
        assert not (await session.get_status())["logged_in"]
        assert attempts == 1  # Back off rather than recreating on every poll.
        session._restore_retry_at = 0
        assert (await session.get_status())["logged_in"]

    asyncio.run(check())
    assert attempts == 2 and store.clears == 0


def test_restore_ignores_entry_outside_the_school_target_host(config, monkeypatch):
    config["employment_entry"] = "https://unrelated.example.test/"
    session = BrowserSession(store=FakeStore(state=SAVED_STATE), desktop=FakeDesktop())
    page = FakePage()
    context = FakeContext([page])

    async def create(visible):
        session.page, session.context = page, context

    monkeypatch.setattr(session, "_create_session", AsyncMock(side_effect=create))
    assert asyncio.run(session.get_status())["logged_in"]
    page.goto.assert_awaited_once_with(LOGIN_URL, wait_until="domcontentloaded", timeout=15000)


def test_cdp_detection_ignores_local_main_page_and_other_context_pages(config):
    auth = FakePage(LOGIN_URL, password_count=1)
    target = FakePage(PORTAL_URL)
    main = FakePage("http://127.0.0.1:8765/")
    session = connected_session(pages=[auth, target, main])

    logged_in, url = asyncio.run(session._detect_logged_in())

    assert logged_in is False
    assert url == LOGIN_URL
    assert session.page is auth
    target.wait_for_load_state.assert_not_awaited()
    main.wait_for_load_state.assert_not_awaited()


def test_owned_browser_can_follow_the_school_target_tab(config):
    auth = FakePage(LOGIN_URL, password_count=1)
    target = FakePage(PORTAL_URL)
    main = FakePage("http://127.0.0.1:8765/")
    session = connected_session(pages=[auth, target, main])
    session._owns_browser = True

    assert asyncio.run(session._detect_logged_in()) == (True, PORTAL_URL)
    assert session.page is target


@pytest.mark.parametrize("embedded", [True, False])
def test_snapshot_excludes_local_app_and_unrelated_browser_storage(config, embedded):
    session = connected_session()
    session.desktop.available = embedded
    storage = deepcopy(SAVED_STATE["storage"])
    storage["cookies"] += [
        {"name": "local-test", "value": "dummy", "domain": "127.0.0.1", "path": "/"},
        {"name": "unrelated-test", "value": "dummy", "domain": "other.example.test", "path": "/"},
    ]
    storage["origins"] += [
        {"origin": "http://127.0.0.1:8765", "localStorage": []},
        {"origin": "https://other.example.test", "localStorage": []},
    ]
    session.context.storage_state = AsyncMock(return_value=storage)
    session.context.cdp_cookies = storage["cookies"]

    assert asyncio.run(session._snapshot()) == SAVED_STATE
    if embedded:
        session.context.storage_state.assert_not_awaited()
        session.context.cookies.assert_not_awaited()
        session.context.new_cdp_session.assert_awaited_once_with(session.page)
        session.context.cdp_connections[0].detach.assert_awaited_once()
        assert session.page.evaluate.await_count == 2
    else:
        session.context.storage_state.assert_awaited_once()
        session.context.cookies.assert_not_awaited()
        session.context.new_cdp_session.assert_not_awaited()
        assert session.page.evaluate.await_count == 1


def test_native_snapshot_uses_existing_view_when_storage_state_would_fail(config):
    session = connected_session()
    session.context.storage_state.side_effect = RuntimeError("native target creation is unsupported")

    assert asyncio.run(session._snapshot()) == SAVED_STATE
    session.context.storage_state.assert_not_awaited()
    session.context.cookies.assert_not_awaited()
    session.context.new_cdp_session.assert_awaited_once_with(session.page)


@pytest.mark.parametrize("operation", ["restore", "snapshot"])
def test_native_cookie_operations_only_attach_to_auth_page_and_detach(config, operation):
    auth = FakePage(PORTAL_URL)
    main = FakePage("http://127.0.0.1:8765/")
    session = connected_session(pages=[auth, main])

    if operation == "restore":
        asyncio.run(session._apply_saved_state(SAVED_STATE))
        session.context.add_cookies.assert_not_awaited()
        expected_method = "Network.setCookies"
    else:
        assert asyncio.run(session._snapshot()) == SAVED_STATE
        session.context.cookies.assert_not_awaited()
        expected_method = "Network.getAllCookies"

    session.context.new_cdp_session.assert_awaited_once_with(auth)
    connection = session.context.cdp_connections[0]
    assert connection.page is auth
    assert connection.send.await_args.args[0] == expected_method
    connection.detach.assert_awaited_once()
    main.evaluate.assert_not_awaited()


@pytest.mark.parametrize("operation", ["restore", "snapshot"])
def test_native_cookie_connection_is_detached_if_protocol_operation_fails(config, operation):
    session = connected_session()
    connection = FakeCDPConnection(session.context, session.page)
    connection.send.side_effect = RuntimeError("test protocol failure")
    session.context.new_cdp_session = AsyncMock(return_value=connection)

    with pytest.raises(RuntimeError, match="test protocol failure"):
        if operation == "restore":
            asyncio.run(session._apply_saved_state(SAVED_STATE))
        else:
            asyncio.run(session._snapshot())

    connection.detach.assert_awaited_once()


def test_cancelling_unfinished_login_disconnects_without_closing_cdp_browser(config):
    session = connected_session(pages=[FakePage(LOGIN_URL, password_count=1)])
    browser, playwright = session.browser, session.playwright

    status = asyncio.run(session.cancel())

    assert not status["logged_in"] and not status["started"] and not status["login_open"]
    assert session.desktop.cancels == 1 and session.desktop.disposals == 1
    playwright.stop.assert_awaited_once()
    browser.close.assert_not_awaited()
    assert session.page is None and session.context is None


def test_closing_authenticated_session_saves_final_state_and_disconnects_cdp(config):
    session = connected_session()
    session._authenticated = True
    browser, playwright = session.browser, session.playwright

    asyncio.run(session.close())

    assert session.store.saved == [SAVED_STATE]
    browser.close.assert_not_awaited()
    playwright.stop.assert_awaited_once()
    assert session.page is None and session.context is None
    assert session._login_open is False


def test_enabling_retention_after_login_saves_current_session(config):
    store = FakeStore(remember=False)
    session = connected_session(store=store)
    session._authenticated = True

    assert asyncio.run(session.set_remember(True)) == {"remember_login": True}
    assert store.saved == [SAVED_STATE]


def test_disabling_retention_after_login_clears_saved_state_without_logging_out(config):
    store = FakeStore(state=SAVED_STATE)
    session = connected_session(store=store)
    session._authenticated = True
    page = session.page

    assert asyncio.run(session.set_remember(False)) == {"remember_login": False}
    assert store.clears == 1
    assert store.saved == []
    assert session._authenticated is True and session.page is page
    session.context.storage_state.assert_not_awaited()


def attachment_client(session):
    response = SimpleNamespace(
        status=200, headers={"content-type": "application/pdf"}, body=AsyncMock(return_value=b"test-pdf-data"))
    client = SimpleNamespace(get=AsyncMock(return_value=response), dispose=AsyncMock())
    session.playwright.request = SimpleNamespace(new_context=AsyncMock(return_value=client))
    return client, response


def test_native_cookie_without_same_site_is_normalized_for_request_storage_schema():
    session = connected_session()
    session.context.cdp_cookies[0].pop("sameSite")
    session.context.cdp_cookies[0]["priority"] = "Medium"
    session.context.cdp_cookies[0]["size"] = 20

    assert asyncio.run(session.native_cookies()) == SAVED_STATE["storage"]["cookies"]
    session.context.new_cdp_session.assert_awaited_once_with(session.page)
    session.context.cdp_connections[0].detach.assert_awaited_once()


def test_native_attachment_download_uses_current_auth_partition_and_disposes_client():
    auth = FakePage(PORTAL_URL)
    main = FakePage("http://127.0.0.1:8765/")
    session = connected_session(store=FakeStore(state=SAVED_STATE), pages=[auth, main])
    current_cookies = deepcopy(SAVED_STATE["storage"]["cookies"])
    current_cookies[0]["value"] = "dummy-current-session"
    current_cookies[0]["partitionKey"] = {"topLevelSite": "https://portal.example.test", "hasCrossSiteAncestor": False}
    session.context.cdp_cookies = current_cookies
    auth.request = SimpleNamespace(get=AsyncMock())
    client, response = attachment_client(session)
    url = "https://files.portal.example.test/protected.pdf"

    assert asyncio.run(session.attachment_content(auth, url)) == (
        200, {"content-type": "application/pdf"}, b"test-pdf-data")

    session.context.new_cdp_session.assert_awaited_once_with(auth)
    session.context.cdp_connections[0].detach.assert_awaited_once()
    request_cookies = deepcopy(current_cookies)
    request_cookies[0].pop("partitionKey")
    session.playwright.request.new_context.assert_awaited_once_with(
        storage_state={"cookies": request_cookies, "origins": []})
    client.get.assert_awaited_once_with(url)
    response.body.assert_awaited_once()
    client.dispose.assert_awaited_once()
    auth.request.get.assert_not_awaited()
    session.context.cookies.assert_not_awaited()
    assert session.store.loads == 0


@pytest.mark.parametrize("failure", ["request", "body"])
def test_native_attachment_client_is_disposed_if_download_fails(failure):
    session = connected_session()
    client, response = attachment_client(session)
    error = RuntimeError("test download failed")
    if failure == "request":
        client.get.side_effect = error
    else:
        response.body.side_effect = error

    with pytest.raises(RuntimeError, match="test download failed"):
        asyncio.run(session.attachment_content(session.page, "https://portal.example.test/protected.pdf"))

    client.dispose.assert_awaited_once()
    session.context.cdp_connections[0].detach.assert_awaited_once()


@pytest.mark.parametrize("embedded", [True, False])
def test_attachment_fallback_keeps_using_requested_page_request_context(embedded):
    session = connected_session()
    session.desktop.available = embedded
    page = FakePage(PORTAL_URL) if embedded else session.page
    response = SimpleNamespace(
        status=206, headers={"content-type": "image/png"}, body=AsyncMock(return_value=b"test-image-data"))
    page.request = SimpleNamespace(get=AsyncMock(return_value=response))
    client, _ = attachment_client(session)
    url = "https://portal.example.test/image.png"

    assert asyncio.run(session.attachment_content(page, url)) == (
        206, {"content-type": "image/png"}, b"test-image-data")

    page.request.get.assert_awaited_once_with(url)
    response.body.assert_awaited_once()
    session.playwright.request.new_context.assert_not_awaited()
    session.context.new_cdp_session.assert_not_awaited()
    client.dispose.assert_not_awaited()
