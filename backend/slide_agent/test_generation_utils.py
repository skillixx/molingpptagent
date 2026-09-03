from backend.slide_agent.slide_agent.generation_utils import (
    consume_page_model_call_budget,
    fallback_slide_for_failed_generation,
    initialize_generation_state,
    item_title_limit,
    normalize_content_page_titles,
    normalize_search_engines,
    parse_last_json_object,
)
from backend.slide_agent.slide_agent.utils import parse_markdown_to_slides


LONG_ITEM_TITLES = [
    "分析餐饮数字化运营效率变化",
    "建立门店经营数据实时监测机制",
    "优化供应链协同与成本控制流程",
    "推动会员精细运营提升复购表现",
]


def _fixed_four_item_outline() -> str:
    """构造 5 章、20 个主题、80 个项目的确定性回归大纲。"""
    lines = ["# 餐饮企业数字化运营", ""]
    for chapter in range(1, 6):
        lines.extend([f"## 第{chapter}章", ""])
        for topic in range(1, 5):
            lines.append(f"### 内容主题{chapter}-{topic}")
            lines.extend(f"- {title}" for title in LONG_ITEM_TITLES)
            lines.append("")
    return "\n".join(lines)


def test_empty_search_selection_disables_all_search_tools():
    assert normalize_search_engines({"search_engine": []}) == []
    assert normalize_search_engines({}) == []


def test_search_selection_keeps_only_supported_explicit_tools():
    assert normalize_search_engines(
        {"search_engine": ["SearchImage", "Unknown", "KnowledgeBaseSearch"]}
    ) == ["SearchImage", "KnowledgeBaseSearch"]


def test_parser_accepts_explanation_and_duplicate_json_objects():
    text = '说明如下：```json\n{"page": 1}\n```\n再次输出：{"page": 2, "data": {"title": "Linux"}}'
    assert parse_last_json_object(text) == {
        "page": 2,
        "data": {"title": "Linux"},
    }


def test_parser_rejects_non_json_text():
    assert parse_last_json_object("仍在生成中") is None


def test_new_generation_resets_stale_page_progress_from_reused_session():
    state = {
        "current_slide_index": 5,
        "retry_count_map": {5: 3},
        "page_model_call_count_map": {5: 20},
        "generated_slides_content": [{"type": "cover"}],
        "last_written_raw": "old invalid output",
        "last_slide_json": {"type": "content"},
        "is_valid_json": True,
        "last_validation_passed": True,
    }
    slides = [
        {"type": "cover", "data": {"title": "Linux 入门"}},
        {"type": "end"},
    ]

    initialize_generation_state(
        state,
        slides=slides,
        markdown="# Linux 入门\n\n## 基础\n### 安装\n- 下载镜像",
        language="zh",
    )

    assert state["current_slide_index"] == 0
    assert state["slides_plan_num"] == 2
    assert state["retry_count_map"] == {}
    assert state["page_model_call_count_map"] == {}
    assert state["generated_slides_content"] == []
    assert state["last_written_raw"] is None
    assert state["last_slide_json"] is None
    assert state["is_valid_json"] is False
    assert state["last_validation_passed"] is None


def test_failed_page_uses_original_outline_schema_instead_of_invalid_text():
    outline = [
        {"type": "cover", "data": {"title": "Linux 入门"}},
        {
            "type": "content",
            "data": {
                "title": "安装 Linux",
                "items": [{"title": "下载镜像", "text": "Detailed content"}],
            },
        },
    ]

    fallback = fallback_slide_for_failed_generation(outline, 1)

    assert fallback["type"] == outline[1]["type"]
    assert fallback["data"]["title"] == outline[1]["data"]["title"]
    assert fallback["data"]["items"] == [{
        "title": "下载镜像",
        "sourceTitle": "下载镜像",
        "text": "Detailed content",
    }]
    assert fallback is not outline[1]


def test_fixed_outline_keeps_twenty_four_item_content_pages_and_all_items_in_order():
    slides = parse_markdown_to_slides(_fixed_four_item_outline())
    content_pages = [slide for slide in slides if slide["type"] == "content"]

    assert len(slides) == 28
    assert len(content_pages) == 20
    assert all(len(page["data"]["items"]) == 4 for page in content_pages)
    assert [
        item["title"]
        for page in content_pages
        for item in page["data"]["items"]
    ] == LONG_ITEM_TITLES * 20


def test_four_item_titles_are_normalized_without_losing_original_information():
    slides = parse_markdown_to_slides(_fixed_four_item_outline())
    normalized_pages = [
        normalize_content_page_titles(slide)
        for slide in slides
        if slide["type"] == "content"
    ]
    normalized_items = [
        item
        for page in normalized_pages
        for item in page["data"]["items"]
    ]

    assert len(normalized_items) == 80
    assert all(len(item["title"]) <= 10 for item in normalized_items)
    assert [item["sourceTitle"] for item in normalized_items] == LONG_ITEM_TITLES * 20
    assert all(item["sourceTitle"] in item["text"] for item in normalized_items)


def test_title_normalization_prefers_agent_short_title_and_is_idempotent():
    source_page = {
        "type": "content",
        "data": {
            "title": "经营效率",
            "items": [
                {
                    "title": "分析餐饮企业数字化运营效率变化",
                    "text": "原始正文",
                }
            ],
        },
    }
    agent_page = {
        "type": "content",
        "data": {
            "title": "经营效率",
            "items": [{"title": "数字化效率", "text": "相关正文"}],
        },
    }

    once = normalize_content_page_titles(agent_page, source_page=source_page)
    twice = normalize_content_page_titles(once, source_page=source_page)

    assert once == twice
    assert once["data"]["items"] == [{
        "title": "数字化效率",
        "sourceTitle": "分析餐饮企业数字化运营效率变化",
        "text": "分析餐饮企业数字化运营效率变化。相关正文",
    }]


def test_title_normalization_uses_safe_fallback_instead_of_truncation():
    page = {
        "type": "content",
        "data": {
            "title": "四项内容",
            "items": [
                {"title": title, "text": "相关正文"}
                for title in LONG_ITEM_TITLES
            ],
        },
    }

    normalized = normalize_content_page_titles(page)

    assert [item["title"] for item in normalized["data"]["items"]] == [
        "核心要点01",
        "核心要点02",
        "核心要点03",
        "核心要点04",
    ]
    assert [item["sourceTitle"] for item in normalized["data"]["items"]] == LONG_ITEM_TITLES


def test_item_title_limits_follow_page_density_protocol():
    assert [item_title_limit(count) for count in (1, 2, 3, 4, 6)] == [
        20,
        16,
        12,
        10,
        10,
    ]


def test_each_page_allows_at_most_two_real_model_calls_and_resets_per_generation():
    state = {}
    slides = [
        {"type": "cover", "data": {"title": "预算测试"}},
        {"type": "content", "data": {"title": "内容", "items": []}},
    ]
    initialize_generation_state(
        state,
        slides=slides,
        markdown="# 预算测试\n\n## 章节\n### 内容",
        language="zh",
    )

    assert consume_page_model_call_budget(state, 0) is True
    assert consume_page_model_call_budget(state, 0) is True
    assert consume_page_model_call_budget(state, 0) is False
    assert consume_page_model_call_budget(state, 1) is True

    initialize_generation_state(
        state,
        slides=slides,
        markdown="# 第二次生成\n\n## 章节\n### 内容",
        language="zh",
    )
    assert consume_page_model_call_budget(state, 0) is True
