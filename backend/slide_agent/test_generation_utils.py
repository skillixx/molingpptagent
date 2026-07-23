from backend.slide_agent.slide_agent.generation_utils import (
    fallback_slide_for_failed_generation,
    initialize_generation_state,
    normalize_search_engines,
    parse_last_json_object,
)


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

    assert fallback == outline[1]
    assert fallback is not outline[1]
