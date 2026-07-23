"""PersonalDB 内部主体到 Chroma 集合名的稳定映射。"""

from __future__ import annotations

import re
from hashlib import sha256


_SUBJECT_PATTERN = re.compile(r"^[A-Za-z0-9:._-]{1,256}$")
_ENVIRONMENTS = {"development", "test", "staging", "production"}


def collection_name_for_subject(subject: int | str) -> str:
    """数字主体保留旧集合；复合主体使用摘要避免字符限制与命名碰撞。"""
    normalized = str(subject).strip()
    if not normalized or not _SUBJECT_PATTERN.fullmatch(normalized):
        raise ValueError("知识库主体格式无效")
    if normalized.isdecimal():
        return f"user_{normalized}"
    parts = normalized.split(":")
    # 当前契约为 moling:<env>:<app_id>:<user_id>，因此拆分后应为4段。
    is_moling = False
    if len(parts) == 4 and parts[0] == "moling":
        is_moling = (
            parts[1] in _ENVIRONMENTS
            and parts[2].isdecimal()
            and int(parts[2]) > 0
            and parts[3].isdecimal()
            and int(parts[3]) > 0
        )
    is_local = len(parts) == 3 and parts[0] == "local" and parts[1] in _ENVIRONMENTS and parts[2] == "trainppt"
    if not (is_moling or is_local):
        raise ValueError("知识库主体格式无效")
    digest = sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return f"subject_{digest}"


def subject_log_tag(subject: int | str) -> str:
    """日志只记录不可逆短摘要，不打印平台用户主体。"""
    normalized = str(subject).strip()
    return sha256(normalized.encode("utf-8")).hexdigest()[:12]


__all__ = ["collection_name_for_subject", "subject_log_tag"]
