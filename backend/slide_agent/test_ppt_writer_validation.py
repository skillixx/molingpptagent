import pytest

from backend.slide_agent.slide_agent.sub_agents.ppt_writer import prompt
from backend.slide_agent.slide_agent.sub_agents.ppt_writer.utils import (
    normalize_repairable_content_slide,
    only_json,
    validate_slide,
)


def _source_page(count: int) -> dict:
    return {
        "type": "content",
        "data": {
            "title": "固定主题",
            "items": [
                {"title": f"第{index}项原始完整标题信息", "text": "原始正文"}
                for index in range(1, count + 1)
            ],
        },
    }


def _valid_agent_page(count: int) -> dict:
    return {
        "type": "content",
        "data": {
            "title": "固定主题",
            "items": [
                {
                    "title": f"短标题{index}",
                    "sourceTitle": f"第{index}项原始完整标题信息",
                    "text": f"第{index}项原始完整标题信息。扩写正文",
                }
                for index in range(1, count + 1)
            ],
        },
    }


def test_only_json_parses_the_first_json_object_from_wrapped_model_text() -> None:
    """历史解析入口必须继续兼容模型在 JSON 前后附加少量说明的情况。"""
    assert only_json('说明 {"type":"content","data":{}} 结束') == {
        "type": "content",
        "data": {},
    }


@pytest.mark.parametrize(
    ("count", "limit"),
    [(1, 20), (2, 16), (3, 12), (4, 10)],
)
def test_content_validation_rejects_titles_over_page_density_limit(
    count: int,
    limit: int,
) -> None:
    source = _source_page(count)
    generated = _valid_agent_page(count)
    generated["data"]["items"][0]["title"] = "长" * (limit + 1)

    valid, errors = validate_slide(generated, source)

    assert valid is False
    assert f"data.items[0].title:最多{limit}字" in errors


def test_content_validation_accepts_short_titles_with_original_information() -> None:
    source = _source_page(4)
    generated = _valid_agent_page(4)

    assert validate_slide(generated, source) == (True, [])


def test_content_validation_requires_original_title_in_source_title_or_body_start() -> None:
    source = _source_page(4)
    generated = _valid_agent_page(4)
    generated["data"]["items"][2].pop("sourceTitle")
    generated["data"]["items"][2]["text"] = "只保留了扩写正文"

    valid, errors = validate_slide(generated, source)

    assert valid is False
    assert "data.items[2]:缺少原始标题信息" in errors


def test_content_validation_rejects_deleted_or_reordered_original_items() -> None:
    source = _source_page(4)
    deleted = _valid_agent_page(4)
    deleted["data"]["items"].pop()
    reordered = _valid_agent_page(4)
    reordered["data"]["items"][0], reordered["data"]["items"][1] = (
        reordered["data"]["items"][1],
        reordered["data"]["items"][0],
    )

    deleted_valid, deleted_errors = validate_slide(deleted, source)
    reordered_valid, reordered_errors = validate_slide(reordered, source)

    assert deleted_valid is False
    assert "data.items:原始项目数量或图表位置无效" in deleted_errors
    assert reordered_valid is False
    assert "data.items[0]:缺少原始标题信息" in reordered_errors


def test_content_validation_allows_one_chart_only_at_the_end() -> None:
    source = _source_page(4)
    generated = _valid_agent_page(4)
    generated["data"]["items"].append({
        "kind": "chart",
        "title": "趋势",
        "text": "图表说明",
        "chartType": "bar",
        "labels": ["A"],
        "series": [{"name": "样本", "data": [1]}],
    })

    assert validate_slide(generated, source) == (True, [])


def test_content_prompt_requires_semantic_compression_and_original_title_retention() -> None:
    content_prompt = prompt.CONTENT_PAGE_PROMPT

    assert "允许压缩 items[*].title，但不得改变原意" in content_prompt
    assert "sourceTitle" in content_prompt
    assert "不得直接截断" in content_prompt
    assert "1 项页面：最多 20 个中文字符" in content_prompt
    assert "2 项页面：最多 16 个中文字符" in content_prompt
    assert "3 项页面：最多 12 个中文字符" in content_prompt
    assert "4 项及以上页面：最多 10 个中文字符" in content_prompt


def test_original_long_titles_are_repaired_locally_without_another_model_call() -> None:
    source = _source_page(5)
    generated = {
        "type": "content",
        "data": {
            "title": "固定主题",
            "items": [
                {"title": item["title"], "text": "模型扩写正文"}
                for item in source["data"]["items"]
            ],
        },
    }
    assert validate_slide(generated, source)[0] is False

    repaired = normalize_repairable_content_slide(generated, source)

    assert validate_slide(repaired, source) == (True, [])
    assert [item["title"] for item in repaired["data"]["items"]] == [
        "核心要点01",
        "核心要点02",
        "核心要点03",
        "核心要点04",
        "核心要点05",
    ]
    assert all(
        item["text"].startswith(item["sourceTitle"])
        for item in repaired["data"]["items"]
    )


def test_repair_does_not_hide_reordered_content_items() -> None:
    source = _source_page(5)
    generated = {
        "type": "content",
        "data": {
            "title": "固定主题",
            "items": [
                {"title": item["title"], "text": "模型扩写正文"}
                for item in source["data"]["items"]
            ],
        },
    }
    generated["data"]["items"][0], generated["data"]["items"][1] = (
        generated["data"]["items"][1],
        generated["data"]["items"][0],
    )

    repaired = normalize_repairable_content_slide(generated, source)

    assert repaired == generated
    assert validate_slide(repaired, source)[0] is False


def test_twenty_five_item_pages_are_repaired_in_one_pass_without_information_loss() -> None:
    pages = []
    for page_index in range(1, 21):
        source = _source_page(5)
        generated = {
            "type": "content",
            "data": {
                "title": f"主题{page_index}",
                "items": [
                    {"title": item["title"], "text": f"第{page_index}页扩写正文"}
                    for item in source["data"]["items"]
                ],
            },
        }
        repaired = normalize_repairable_content_slide(generated, source)
        assert validate_slide(repaired, source) == (True, [])
        pages.append(repaired)

    items = [item for page in pages for item in page["data"]["items"]]
    assert len(items) == 100
    assert all(len(item["title"]) <= 10 for item in items)
    assert all(item["text"].startswith(item["sourceTitle"]) for item in items)
