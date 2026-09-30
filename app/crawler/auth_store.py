"""Local, optional session retention. Windows encrypts tokens for this user."""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path

from ..settings import DATA_DIR


def _windows_crypt(data: bytes, decrypt: bool = False) -> bytes:
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), buffer)
    result = Blob()
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    if decrypt:
        function = crypt32.CryptUnprotectData
        function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    else:
        function = crypt32.CryptProtectData
        function.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    description = None if decrypt else "知序本机登录状态"
    if not function(ctypes.byref(source), description, None, None, None, 1, ctypes.byref(result)):
        raise OSError("无法访问本机加密登录状态。")
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel32.LocalFree(result.data)


class AuthStore:
    def __init__(self, directory: Path = DATA_DIR):
        self.directory = directory
        self.preferences = directory / "auth_preferences.json"
        self.state_path = directory / "auth_state.bin"
        self.legacy_path = directory / "playwright_state.json"

    def remembers(self) -> bool:
        try:
            return json.loads(self.preferences.read_text(encoding="utf-8")).get("remember_login") is True
        except (OSError, ValueError, AttributeError):
            return True

    def set_remember(self, value: bool) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self.preferences.write_text(json.dumps({"remember_login": value}), encoding="utf-8")
        if not value:
            self.clear()

    def load(self) -> dict | None:
        if not self.remembers():
            return None
        try:
            if self.state_path.is_file():
                data = self.state_path.read_bytes()
                if data.startswith(b"DPAPI\0"):
                    data = _windows_crypt(data[6:], decrypt=True)
                elif data.startswith(b"JSON\0"):
                    data = data[5:]
                else:
                    return None
                state = json.loads(data)
            elif self.legacy_path.is_file():
                state = {"storage": json.loads(self.legacy_path.read_text(encoding="utf-8")), "session": {}}
            else:
                return None
            return state if isinstance(state, dict) and isinstance(state.get("storage"), dict) else None
        except (OSError, ValueError):
            return None

    def save(self, state: dict) -> None:
        if not self.remembers():
            return
        data = json.dumps(state, ensure_ascii=False).encode("utf-8")
        data = b"DPAPI\0" + _windows_crypt(data) if os.name == "nt" else b"JSON\0" + data
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(self.state_path)
        self.legacy_path.unlink(missing_ok=True)

    def clear(self) -> None:
        self.state_path.unlink(missing_ok=True)
        self.state_path.with_suffix(".tmp").unlink(missing_ok=True)
        self.legacy_path.unlink(missing_ok=True)
