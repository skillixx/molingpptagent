import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from core.markitdown_converter import MarkItDownConverter


class _FakeMarkItDown:
    """测试替身：确认旧版 DOC 会先转换为 DOCX。"""

    def convert(self, file_path: str):
        converted_path = Path(file_path)
        assert converted_path.suffix.lower() == ".docx"
        assert converted_path.exists()
        return SimpleNamespace(text_content="旧版 Word 文档转换成功")


def test_convert_legacy_doc_via_docx_fallback(tmp_path, monkeypatch):
    """旧版 .doc 应通过 Word 回退为 .docx，再交给 MarkItDown。"""
    source_path = tmp_path / "legacy.doc"
    source_path.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1"))

    converter = MarkItDownConverter(enable_cache=False, use_magic_pdf=False)
    monkeypatch.setattr(converter, "_get_markitdown_instance", lambda: _FakeMarkItDown())

    def fake_convert_to_docx(source: Path, destination: Path):
        assert source == source_path
        destination.write_bytes(b"fake-docx")

    monkeypatch.setattr(converter, "_convert_legacy_doc_to_docx", fake_convert_to_docx)

    content, encoding = converter.convert_file(str(source_path))

    assert content == "旧版 Word 文档转换成功"
    assert encoding == "utf-8"


def test_word_cleanup_failure_does_not_override_success(tmp_path, monkeypatch):
    """Word 已完成保存时，关闭阶段的 RPC 异常不应覆盖转换成功。"""
    source_path = tmp_path / "legacy.doc"
    destination_path = tmp_path / "legacy.docx"
    source_path.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1"))

    class FakeDocument:
        def SaveAs2(self, output_path: str, FileFormat: int):
            assert FileFormat == 16
            Path(output_path).write_bytes(b"fake-docx")

        def Close(self, SaveChanges: bool):
            raise RuntimeError("模拟 Word 文档已经自行关闭")

    class FakeWord:
        Visible = False
        DisplayAlerts = 0

        def __init__(self):
            self.Documents = SimpleNamespace(Open=lambda *args, **kwargs: FakeDocument())

        def Quit(self):
            raise RuntimeError("模拟 Word 进程已经自行退出")

    pythoncom_module = ModuleType("pythoncom")
    pythoncom_module.CoInitialize = lambda: None
    pythoncom_module.CoUninitialize = lambda: None
    win32com_module = ModuleType("win32com")
    win32com_client_module = ModuleType("win32com.client")
    win32com_client_module.DispatchEx = lambda _: FakeWord()
    win32com_module.client = win32com_client_module
    monkeypatch.setitem(sys.modules, "pythoncom", pythoncom_module)
    monkeypatch.setitem(sys.modules, "win32com", win32com_module)
    monkeypatch.setitem(sys.modules, "win32com.client", win32com_client_module)

    converter = MarkItDownConverter(enable_cache=False, use_magic_pdf=False)
    converter._convert_legacy_doc_to_docx(source_path, destination_path)

    assert destination_path.read_bytes() == b"fake-docx"
