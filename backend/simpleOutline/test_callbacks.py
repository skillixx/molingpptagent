import io
from contextlib import redirect_stdout

from backend.simpleOutline.callbacks import after_tool_callback


class FakeTool:
    name = "DocumentSearch"


def test_tool_callback_does_not_write_unicode_payload_to_gbk_stdout() -> None:
    """搜索结果含 GBK 不支持字符时，回调也不能让大纲流中断。"""
    raw_stdout = io.BytesIO()
    gbk_stdout = io.TextIOWrapper(raw_stdout, encoding="gbk", errors="strict")

    with redirect_stdout(gbk_stdout):
        after_tool_callback(FakeTool(), {}, None, {"result": "价格 ₳100"})
        gbk_stdout.flush()

    assert raw_stdout.getvalue() == b""
