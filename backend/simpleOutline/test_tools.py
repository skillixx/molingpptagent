import asyncio

from backend.simpleOutline import tools


class FakeToolContext:
    agent_name = "outline_agent"

    def __init__(self) -> None:
        self.state = {"metadata": {"language": "中文"}}


def test_document_search_uses_one_compact_article(monkeypatch) -> None:
    """搜索只抓取一篇并限制正文长度，避免大纲生成长时间卡住。"""
    article_requests: list[str] = []
    monkeypatch.setattr(tools, "sogou_weixin_search", lambda keyword: [
        {"title": "第一篇", "link": "sogou-1", "publish_time": "2026-01-01"},
        {"title": "第二篇", "link": "sogou-2", "publish_time": "2026-01-02"},
    ])
    monkeypatch.setattr(tools, "get_real_url", lambda url: f"https://example.test/{url}")

    def fake_content(url: str, referer: str) -> str:
        article_requests.append(referer)
        return "资料" * 4000

    monkeypatch.setattr(tools, "get_article_content", fake_content)
    context = FakeToolContext()

    result = asyncio.run(tools.DocumentSearch("Linux 入门", context))

    assert article_requests == ["sogou-1"]
    assert len(result) == 1
    assert len(result[0]["content"]) == 6000
    assert "content" not in context.state["metadata"]["tool_document_ids"][0]

    repeated_result = asyncio.run(tools.DocumentSearch("Linux 权限", context))
    assert "立即输出 Markdown 大纲" in repeated_result
    assert article_requests == ["sogou-1"]
