from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path
from typing import Any
import yaml

RESOURCE_ROOT = Path(__file__).resolve().parents[1]


def runtime_root() -> Path:
    if not getattr(sys, "frozen", False):
        return RESOURCE_ROOT
    exe_dir = Path(sys.executable).resolve().parent
    project_dir = exe_dir.parent.parent
    if (project_dir / "launcher.py").is_file() and (project_dir / "data").is_dir():
        return project_dir
    return exe_dir


ROOT = runtime_root()
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
DIRS = {name: DATA_DIR / name for name in ["raw_json", "raw_html", "article_text", "attachments", "extracted_text", "database", "indexes", "exports", "logs", "diagnostics"]}
DEFAULT_CONFIG: dict[str, Any] = {
    "portal_url": "https://TODO-PORTAL-URL", "allowed_domains": ["TODO-ALLOWED-DOMAIN"],
    "employment_entry": "https://TODO-EMPLOYMENT-ENTRY", "list_item_selector": "TODO_LIST_ITEM_SELECTOR",
    "title_selector": "TODO_TITLE_SELECTOR", "date_selector": "TODO_DATE_SELECTOR",
    "detail_link_selector": "TODO_DETAIL_LINK_SELECTOR", "next_button_selector": "TODO_NEXT_BUTTON_SELECTOR",
    "detail_body_selector": "TODO_DETAIL_BODY_SELECTOR", "attachment_selector": "TODO_ATTACHMENT_SELECTOR",
    "detail_open_mode": "link",
    "data_source": "page", "api_keywords": ["选调经验"],
    "api_notice_type": 10,
    "api_detail_url_template": "https://my.muc.edu.cn/page/11#/print?notice_id={notice_id}&show_type=1&type={notice_type}",
    "login_page_markers": ["登录", "统一认证"], "page_interval_seconds": 1.5,
}

def ensure_directories() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_DIR != RESOURCE_ROOT / "config":
        for name in ("cities.txt", "majors.txt", "portal.example.yaml"):
            source = RESOURCE_ROOT / "config" / name
            destination = CONFIG_DIR / name
            if source.is_file() and not destination.exists():
                shutil.copyfile(source, destination)
    for directory in DIRS.values():
        directory.mkdir(parents=True, exist_ok=True)
        keep = directory / ".gitkeep"
        keep.touch(exist_ok=True)

def config_path() -> Path: return CONFIG_DIR / "portal.yaml"

def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return DEFAULT_CONFIG.copy()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {**DEFAULT_CONFIG, **data}
    except yaml.YAMLError:
        return DEFAULT_CONFIG.copy()

def save_config(data: dict[str, Any]) -> dict[str, Any]:
    CONFIG_DIR.mkdir(exist_ok=True)
    merged = {**DEFAULT_CONFIG, **data}
    config_path().write_text(yaml.safe_dump(merged, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return merged

def safe_filename(name: str, fallback: str = "file") -> str:
    name = Path(name or fallback).name
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(". ")
    return (name[:160] or fallback)

def is_allowed_url(url: str, config: dict[str, Any]) -> bool:
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ""
    return any(rule and rule != "TODO-ALLOWED-DOMAIN" and (host == rule or host.endswith("." + rule)) for rule in config.get("allowed_domains", []))
