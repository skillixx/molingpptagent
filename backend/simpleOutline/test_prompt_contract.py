from backend.simpleOutline import prompt


def test_outline_prompt_never_generates_more_than_four_items_per_topic() -> None:
    assert "每个二级小节列出3–4个要点" in prompt.OUTLINE_INSTRUCTION_WITH_SEARCH
    assert "每个二级小节列出3–4个要点" in prompt.OUTLINE_INSTRUCTION_NO_SEARCH
    assert "3–5个要点" not in prompt.OUTLINE_INSTRUCTION_WITH_SEARCH
    assert "3–5个要点" not in prompt.OUTLINE_INSTRUCTION_NO_SEARCH
