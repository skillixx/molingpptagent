from pathlib import Path

import pytest

from backend.main_api.template_assets import resolve_template_asset


def test_template_asset_path_does_not_depend_on_working_directory(monkeypatch) -> None:
    """从仓库根目录启动时，也必须读取主 API 包内的模板成品。"""
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.chdir(repository_root)

    asset_path = resolve_template_asset("template_1.jpg")

    assert asset_path == repository_root / "backend" / "main_api" / "template" / "template_1.jpg"
    assert asset_path.is_file()


@pytest.mark.parametrize("filename", ["../.env", "missing-template.jpg", ""])
def test_template_asset_rejects_unsafe_or_missing_file(filename: str) -> None:
    """非法路径和不存在的资源不能被静态接口读取。"""
    with pytest.raises(FileNotFoundError):
        resolve_template_asset(filename)
