"""检查通知列表接口的请求体和返回结构，不输出 Cookie 或认证请求头。"""
from __future__ import annotations

import asyncio
import json

from playwright.async_api import async_playwright

from app.settings import DATA_DIR, load_config


def describe(value, depth: int = 0):
    if depth >= 3:
        return type(value).__name__
    if isinstance(value, dict):
        return {key: describe(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return {"type": "list", "length": len(value), "first": describe(value[0], depth + 1) if value else None}
    return type(value).__name__


async def main() -> None:
    config = load_config()
    state_path = DATA_DIR / "playwright_state.json"
    if not state_path.is_file():
        raise SystemExit("没有登录状态，请先登录并点击“我已登录”。")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=str(state_path))
        page = await context.new_page()
        captured = []

        async def inspect_response(response):
            if "/getNoticeByPage" not in response.url:
                return
            try:
                request_json = response.request.post_data_json
            except Exception:
                request_json = response.request.post_data
            try:
                response_json = await response.json()
            except Exception:
                response_json = None
            tables = None
            if isinstance(response_json, dict):
                datas = response_json.get("datas")
                if isinstance(datas, dict):
                    tables = datas.get("tables")
            captured.append({
                "url": response.url,
                "method": response.request.method,
                "request_body": request_json,
                "response_shape": describe(response_json),
                "row_count": len(tables) if isinstance(tables, list) else None,
                "first_row": tables[0] if isinstance(tables, list) and tables else None,
            })

        page.on("response", inspect_response)
        await page.goto(config["employment_entry"], wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        await browser.close()

    if not captured:
        raise SystemExit("没有捕获到 getNoticeByPage 请求。")
    output = DATA_DIR / "diagnostics" / "notice_api_shape.json"
    output.write_text(json.dumps(captured[-1], ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(captured[-1], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
