"""用于区分正在运行的旧版后端与当前工作区代码。"""
from hashlib import sha256
from pathlib import Path


def current_version() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = sha256()
    paths = [root / "launcher.py", *sorted((root / "app").rglob("*")), *sorted((root / "frontend" / "dist").rglob("*"))]
    for path in paths:
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"}:
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


APP_VERSION = current_version()
