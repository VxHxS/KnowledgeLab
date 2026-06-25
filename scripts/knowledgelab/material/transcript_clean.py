"""Transcript post-processing: regex cleanup + LLM polishing."""
from __future__ import annotations

import re


PARASITE_WORDS = [
    "ну", "ээ", "эээ", "эм", "эмм", "как бы", "то есть", "вот", "короче",
    "типа", "так сказать", "значит", "собственно", "в общем", "кстати",
    "видишь ли", "скажем", "допустим", "блин", "короче говоря",
]


def clean_transcript_regex(text: str) -> str:
    """Basic regex-based transcript cleanup: dedup, punctuation, parasites."""
    if not text or not text.strip():
        return text

    lines = text.split("\n")
    cleaned: list[str] = []
    prev_line = ""

    for line in lines:
        line = line.strip()
        if not line:
            if cleaned and cleaned[-1]:
                cleaned.append("")
            continue

        if line == prev_line:
            continue

        for parasite in PARASITE_WORDS:
            pattern = rf"\b{re.escape(parasite)}\b"
            line = re.sub(pattern, "", line, flags=re.IGNORECASE)

        line = re.sub(r"\s{2,}", " ", line).strip()

        line = re.sub(r"\.\.\.+", "...", line)
        line = re.sub(r",,+", ",", line)
        line = re.sub(r"\?\?+", "?", line)
        line = re.sub(r"!!+", "!", line)
        line = re.sub(r"\s+([.,!?;:])", r"\1", line)

        if line and not line[0].isupper() and prev_line and prev_line.endswith((".", "!", "?", "...")):
            line = line[0].upper() + line[1:]

        if line:
            cleaned.append(line)
            prev_line = line
        elif cleaned and cleaned[-1]:
            cleaned.append("")

    result = "\n".join(cleaned).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def clean_transcript_llm(text: str, base_url: str, model: str, timeout: int = 120) -> str:
    """LLM-based transcript polishing: fix punctuation, grammar, style."""
    if not text or not text.strip():
        return text

    from knowledgelab.llm.lmstudio import call_plain_lmstudio

    chunk_size = 3000
    chunks: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    polished_chunks: list[str] = []
    for chunk in chunks:
        prompt = (
            "Исправь пунктуацию, грамматику и стиль этого транскрипта.\n"
            "Сохрани смысл и все детали. Не добавляй информацию, которой нет в тексте.\n"
            "Не пиши комментарии — верни только исправленный текст.\n\n"
            f"{chunk}"
        )
        result, _ = call_plain_lmstudio(prompt, base_url, model, timeout=min(timeout, 60), max_tokens=2000)
        polished_chunks.append(result.strip() if result else chunk)

    return "\n\n".join(polished_chunks)
