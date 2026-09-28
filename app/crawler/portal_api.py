from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode

from ..settings import DIRS

LIST_API_MARKER = "/comsys-portal-notice-web/getNoticeByPage"
TEMPLATE_PATH = DIRS["diagnostics"] / "notice_api_template.json"

PAGE_KEYS = {"page", "pagenum", "pageno", "pageindex", "currentpage", "current"}
KEYWORD_KEYS = {
    "keyword", "keywords", "search", "searchkey", "searchvalue", "searchcontent",
    "title", "noticetitle", "subject",
}


class PortalApiError(RuntimeError):
    pass


def _normal_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _safe_headers(headers: dict[str, str]) -> dict[str, str]:
    allowed = {"accept", "content-type", "x-requested-with", "accept-language"}
    return {key: value for key, value in headers.items() if key.lower() in allowed}


def _parse_request_body(request) -> tuple[Any, str]:
    content_type = (request.headers.get("content-type") or "").lower()
    raw = request.post_data or ""
    if "application/x-www-form-urlencoded" in content_type:
        return dict(parse_qsl(raw, keep_blank_values=True)), "form"
    try:
        value = request.post_data_json
        if value is not None:
            return value, "json"
    except Exception:
        pass
    try:
        return dict(parse_qsl(raw, keep_blank_values=True)), "form"
    except Exception:
        return raw, "raw"


def template_from_response(response) -> dict[str, Any]:
    body, body_format = _parse_request_body(response.request)
    return {
        "url": response.url,
        "method": response.request.method,
        "headers": _safe_headers(response.request.headers),
        "body": body,
        "body_format": body_format,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_template(template: dict[str, Any]) -> None:
    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_PATH.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")


def load_template() -> dict[str, Any] | None:
    if not TEMPLATE_PATH.is_file():
        return None
    try:
        return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


async def remember_response(response) -> None:
    if LIST_API_MARKER not in response.url:
        return
    save_template(template_from_response(response))


def install_api_capture(context) -> None:
    import asyncio

    def on_response(response):
        if LIST_API_MARKER in response.url:
            asyncio.create_task(remember_response(response))

    context.on("response", on_response)


async def capture_first_page(page, entry_url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        async with page.expect_response(lambda response: LIST_API_MARKER in response.url, timeout=20000) as info:
            await page.goto(entry_url, wait_until="domcontentloaded")
        response = await info.value
        result = await response.json()
    except Exception as exc:
        raise PortalApiError(f"未捕获到通知列表接口：{exc}") from exc
    template = template_from_response(response)
    save_template(template)
    return result, template


def _update_nested(value: Any, aliases: set[str], replacement: Any) -> bool:
    found = False
    if isinstance(value, dict):
        for key, item in value.items():
            if _normal_key(str(key)) in aliases:
                value[key] = replacement
                found = True
            elif isinstance(item, (dict, list)) and _update_nested(item, aliases, replacement):
                found = True
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)) and _update_nested(item, aliases, replacement):
                found = True
    return found


def prepare_body(template: dict[str, Any], page_offset: int, keyword: str | None, absolute_page: int | None = None) -> tuple[str | None, bool, bool]:
    body = copy.deepcopy(template.get("body"))
    if not isinstance(body, (dict, list)):
        return (str(body) if body else None), page_offset == 0, not keyword

    page_found = False
    if isinstance(body, (dict, list)):
        # 先找原始页码值，保持接口的0起始或1起始习惯。
        def advance(value: Any) -> bool:
            changed = False
            if isinstance(value, dict):
                for key, item in value.items():
                    if _normal_key(str(key)) in PAGE_KEYS and isinstance(item, (int, str)):
                        try:value[key] = absolute_page if absolute_page is not None else int(item) + page_offset
                        except (TypeError, ValueError):continue
                        changed = True
                    elif isinstance(item, (dict, list)) and advance(item):changed = True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, (dict, list)) and advance(item):changed = True
            return changed
        page_found = advance(body)

    keyword_found = True
    if keyword:
        keyword_found = _update_nested(body, KEYWORD_KEYS, keyword)

    if template.get("body_format") == "form" and isinstance(body, dict):
        return urlencode(body), page_found, keyword_found
    return json.dumps(body, ensure_ascii=False), page_found, keyword_found


async def fetch_page(page, template: dict[str, Any], page_offset: int, keyword: str | None) -> dict[str, Any]:
    # 门户会记住用户上次停留的页码，因此这里明确指定第1、2、3……页。
    body, page_found, keyword_found = prepare_body(template, page_offset, keyword, absolute_page=page_offset+1)
    if page_offset and not page_found:
        raise PortalApiError("无法从请求体识别页码字段")
    if keyword and not keyword_found:
        raise PortalApiError("无法从请求体识别搜索关键词字段")
    result = await page.evaluate(
        """async ({url, method, headers, body}) => {
          const response = await fetch(url, {method, headers, body, credentials: 'include'});
          const text = await response.text();
          if (!response.ok) throw new Error(`HTTP ${response.status}: ${text.slice(0, 200)}`);
          return JSON.parse(text);
        }""",
        {"url": template["url"], "method": template.get("method", "POST"),
         "headers": template.get("headers", {}), "body": body},
    )
    if not isinstance(result, dict):
        raise PortalApiError("列表接口没有返回JSON对象")
    return result


def extract_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    datas = result.get("datas")
    tables = datas.get("tables") if isinstance(datas, dict) else None
    if not isinstance(tables, list):
        raise PortalApiError("接口响应中没有 datas.tables 列表")
    return [row for row in tables if isinstance(row, dict)]


def _value(row: dict[str, Any], aliases: set[str]) -> Any:
    for key, value in row.items():
        if _normal_key(str(key)) in aliases and value not in (None, ""):
            return value
    return None


def normalize_notice(row: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    notice_id = _value(row, {"noticeid", "noticeoid", "id", "infoid", "businessid", "oid"})
    title = _value(row, {"noticetitle", "noticename", "title", "subject", "name"})
    published = _value(row, {"publishtime", "publishdate", "releasetime", "releasedate", "sendtime", "senddate", "createtime", "noticedate"})
    notice_type = _value(row, {"noticetypeid", "noticecategoryid", "typeid", "categoryid"})
    if notice_type is None or not str(notice_type).isdigit():
        notice_type = config.get("api_notice_type", 10)
    if notice_id is None or not title:
        raise PortalApiError(f"无法识别通知ID或标题，返回字段为：{', '.join(row.keys())}")
    template = config.get(
        "api_detail_url_template",
        "https://my.muc.edu.cn/page/11#/print?notice_id={notice_id}&show_type=1&type={notice_type}",
    )
    return {
        "portal_id": str(notice_id),
        "title": str(title).strip(),
        "published_at": str(published or "").strip(),
        "detail_url": template.format(notice_id=notice_id, notice_type=notice_type),
        "category": "就业信息",
        "raw_api": row,
    }


def save_raw_page(result: dict[str, Any], keyword: str, page_number: int) -> Path:
    safe_keyword = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", keyword or "all")[:40]
    path = DIRS["raw_json"] / f"{safe_keyword}_page_{page_number}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
