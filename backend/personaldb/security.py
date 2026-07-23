"""PersonalDB 文件输入的最小安全规范化。"""

from __future__ import annotations


def safe_upload_filename(filename: str | None) -> str:
    """仅保留最终文件名，阻断斜杠、反斜杠、控制字符和超长路径。"""
    raw = (filename or "uploaded_file").replace("\\", "/")
    candidate = raw.rsplit("/", 1)[-1].strip()
    if (
        not candidate
        or candidate in {".", ".."}
        or any(ord(character) < 32 for character in candidate)
    ):
        return "uploaded_file"
    return candidate[:255]


__all__ = ["safe_upload_filename"]
