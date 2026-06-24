from __future__ import annotations

from knowledgelab.utils.text import compact_whitespace


def github_user_hint(text: str, url: str) -> str:
    hint = text
    candidates = {
        url,
        url.replace("https://", "", 1),
        url.replace("https://www.", "www.", 1),
    }
    for candidate in sorted(candidates, key=len, reverse=True):
        if candidate and candidate in hint:
            hint = hint.replace(candidate, "", 1)
            break
    hint = hint.strip()
    return hint or "_No hint was provided._"
