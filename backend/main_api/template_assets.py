"""模板静态资源路径解析。"""

from pathlib import Path


# 路径固定在主 API 包内，避免服务从不同工作目录启动时读到错误的 template 目录。
TEMPLATE_ASSET_DIR = Path(__file__).resolve().parent / "template"


def resolve_template_asset(filename: str) -> Path:
    """返回存在的模板资源；拒绝目录跳转和不存在的文件。"""
    if not filename or Path(filename).name != filename:
        raise FileNotFoundError(filename)

    asset_path = TEMPLATE_ASSET_DIR / filename
    if not asset_path.is_file():
        raise FileNotFoundError(filename)
    return asset_path
