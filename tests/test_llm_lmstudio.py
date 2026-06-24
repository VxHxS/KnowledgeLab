from __future__ import annotations

from knowledgelab.llm.lmstudio import extract_chat_content, is_vision_model_name


def test_is_vision_model_name_vl():
    assert is_vision_model_name("qwen2.5-vl-7b") is True


def test_is_vision_model_name_llava():
    assert is_vision_model_name("llava-1.6") is True


def test_is_vision_model_name_vision():
    assert is_vision_model_name("some-vision-model") is True


def test_is_vision_model_name_not_vision():
    assert is_vision_model_name("qwen3-14b") is False


def test_is_vision_model_name_empty():
    assert is_vision_model_name("") is False


def test_extract_chat_content_valid():
    response = {
        "choices": [{"message": {"content": "Hello!", "reasoning_content": "thinking..."}}]
    }
    content, reasoning = extract_chat_content(response)
    assert content == "Hello!"
    assert reasoning == "thinking..."


def test_extract_chat_content_no_reasoning():
    response = {"choices": [{"message": {"content": "Response"}}]}
    content, reasoning = extract_chat_content(response)
    assert content == "Response"
    assert reasoning == ""


def test_extract_chat_content_empty_choices():
    content, reasoning = extract_chat_content({"choices": []})
    assert content == ""
    assert reasoning == ""


def test_extract_chat_content_malformed():
    content, reasoning = extract_chat_content({})
    assert content == ""
    assert reasoning == ""


def test_extract_chat_content_none_content():
    response = {"choices": [{"message": {"content": None}}]}
    content, reasoning = extract_chat_content(response)
    assert content == ""
