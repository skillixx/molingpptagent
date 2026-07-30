"""在显式确认后执行一致性 MySQL 备份，并输出不含凭据的校验摘要。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url


def build_dump_command(database_url: str, executable: str) -> tuple[list[str], str, str]:
    """结构化解析连接串，密码仅通过子进程环境传递。"""
    parsed = make_url(database_url)
    if parsed.get_backend_name() != "mysql" or not parsed.database:
        raise RuntimeError("备份只支持明确数据库名的 MySQL")
    if not parsed.host or not parsed.username or parsed.password is None:
        raise RuntimeError("生产数据库备份配置不完整")
    command = [
        executable,
        f"--host={parsed.host}",
        f"--port={parsed.port or 3306}",
        f"--user={parsed.username}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--events",
        "--hex-blob",
        "--no-tablespaces",
        "--databases",
        parsed.database,
    ]
    return command, parsed.database, parsed.password


def _sha256_file(path: Path) -> str:
    """流式计算大备份摘要，避免把完整生产库载入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TrainPPTAgent 生产数据库备份")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--confirm", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    expected_confirmation = f"BACKUP-{args.expected_database}-{args.release_commit}"
    if args.confirm != expected_confirmation:
        print(json.dumps({"completed": False, "reason": "备份确认文本不匹配"}, ensure_ascii=False))
        return 2
    values = dotenv_values(args.env_file)
    database_url = str(values.get("DATABASE_URL") or "")
    executable = shutil.which("mysqldump")
    if not executable:
        print(json.dumps({"completed": False, "reason": "mysqldump 不可用"}, ensure_ascii=False))
        return 2
    try:
        command, database_name, password = build_dump_command(database_url, executable)
    except RuntimeError as exc:
        print(json.dumps({"completed": False, "reason": str(exc)}, ensure_ascii=False))
        return 2
    if database_name != args.expected_database:
        print(json.dumps({"completed": False, "reason": "数据库名与授权目标不一致"}, ensure_ascii=False))
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_dir / f"{database_name}-{timestamp}-{args.release_commit[:12]}.sql"
    child_environment = {**os.environ, "MYSQL_PWD": password}
    try:
        with output.open("xb") as stream:
            os.chmod(output, 0o600)
            completed = subprocess.run(
                command,
                stdout=stream,
                stderr=subprocess.PIPE,
                env=child_environment,
                check=False,
            )
        if completed.returncode != 0 or output.stat().st_size == 0:
            output.unlink(missing_ok=True)
            print(json.dumps({"completed": False, "reason": "mysqldump 执行失败"}, ensure_ascii=False))
            return 2
        digest = _sha256_file(output)
    except OSError:
        output.unlink(missing_ok=True)
        print(json.dumps({"completed": False, "reason": "备份文件写入失败"}, ensure_ascii=False))
        return 2

    print(json.dumps({
        "completed": True,
        "database": database_name,
        "file": str(output.resolve()),
        "bytes": output.stat().st_size,
        "sha256": digest,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
