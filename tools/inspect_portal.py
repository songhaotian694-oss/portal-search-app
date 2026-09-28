"""使用本地登录状态检查门户列表和一篇详情，不输出 Cookie。"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.settings import DATA_DIR, load_config


async def main() -> None:
    config = load_config()
    state_path = DATA_DIR / "playwright_state.json"
    if not state_path.is_file():
        raise SystemExit("没有已保存的登录状态，请先在软件中登录并点击“我已登录”。")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=str(state_path))
        page = await context.new_page()
        responses = []
        page.on("response", lambda response: responses.append(response))
        await page.goto(config["employment_entry"], wait_until="domcontentloaded")
        rows = page.locator(config["list_item_selector"])
        await rows.first.wait_for(state="visible", timeout=15000)
        list_count = await rows.count()
        title = (await rows.first.locator(config["title_selector"]).inner_text()).strip()
        before = page.url
        before_html = await page.content()
        list_responses = list(responses)
        responses.clear()
        await rows.first.locator(config["title_selector"]).click()
        await page.wait_for_timeout(2500)
        pages = [item for item in context.pages if not item.is_closed()]
        detail_page = pages[-1]
        detail_url = detail_page.url
        html = await detail_page.content()
        soup = BeautifulSoup(html, "html.parser")
        for node in soup.select("input[type=password],input[name*=password i]"):
            node["value"] = "[已移除]"
        for node in soup.select("script"):
            node.decompose()
        out = DATA_DIR / "diagnostics" / "detail_page_sanitized.html"
        out.write_text(str(soup), encoding="utf-8")
        visible_dialogs = await detail_page.locator(".el-dialog:visible").count()
        visible_iframes = await detail_page.locator("iframe:visible").count()
        detail_body_count = await detail_page.locator(config["detail_body_selector"]).count()
        attachment_count = await detail_page.locator(config["attachment_selector"]).count()
        if detail_page is not page:
            await detail_page.close()
        next_button = page.locator(config["next_button_selector"]).first
        old_title = title
        await next_button.click()
        await page.wait_for_function(
            "([selector, oldText]) => { const el=document.querySelector(selector); return el && el.innerText.trim() !== oldText; }",
            arg=[config["title_selector"], old_title], timeout=15000
        )
        next_title = (await page.locator(config["title_selector"]).first.inner_text()).strip()
        print(json.dumps({
            "list_count": list_count,
            "first_title": title,
            "before_url": before,
            "detail_url": detail_url,
            "detail_opened": detail_url != before or html != before_html,
            "open_pages": len(pages),
            "visible_dialogs": visible_dialogs,
            "visible_iframes": visible_iframes,
            "detail_body_count": detail_body_count,
            "attachment_count": attachment_count,
            "next_page_changed": next_title != old_title,
            "list_requests": sorted({
                urlunsplit((*urlsplit(item.url)[:3], "", ""))
                for item in list_responses
                if item.request.resource_type in {"xhr", "fetch"}
            }),
            "click_requests": sorted({
                urlunsplit((*urlsplit(item.url)[:3], "", ""))
                for item in responses
                if item.request.resource_type in {"xhr", "fetch"}
            }),
            "saved_path": str(out),
        }, ensure_ascii=False))
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
