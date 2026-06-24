from __future__ import annotations

import json
import urllib.request

from knowledgelab.models import CodePenSnapshot
from knowledgelab.utils.text import compact_whitespace, markdown_fence_text
from knowledgelab.utils.urls import parse_codepen_url


def fetch_codepen_snapshot(url: str, *, timeout: int = 15, limit_bytes: int = 600_000) -> CodePenSnapshot:
    metadata = parse_codepen_url(url)
    if not metadata:
        return CodePenSnapshot("blocked", "", "", "", reason="not a CodePen pen URL")
    title = ""
    author = metadata.get("codepen_owner", "")
    description = ""
    try:
        request = urllib.request.Request(
            metadata["codepen_oembed_url"],
            headers={"User-Agent": "KnowledgeLab/1.0 (+local Obsidian capture)"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read(limit_bytes).decode("utf-8", errors="replace") or "{}")
        title = str(data.get("title") or "").strip()
        author = str(data.get("author_name") or author).strip()
        description = compact_whitespace(str(data.get("html") or ""))[:800]
    except Exception as exc:
        return CodePenSnapshot("blocked", title, author, description, reason=str(exc))

    code_parts: dict[str, str] = {}
    for suffix, key in ((".html", "html_code"), (".css", "css_code"), (".js", "js_code")):
        code_url = f"{metadata['codepen_url']}{suffix}"
        try:
            request = urllib.request.Request(code_url, headers={"User-Agent": "KnowledgeLab/1.0 (+local Obsidian capture)"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                text = response.read(limit_bytes).decode("utf-8", errors="replace")
            if "cloudflare" in text.lower() and "security" in text.lower():
                continue
            code_parts[key] = text.strip()[:120000]
        except Exception:
            continue
    status = "extracted" if any(code_parts.values()) else "metadata"
    return CodePenSnapshot(
        status,
        title or f"CodePen {metadata.get('codepen_id', '')}",
        author,
        description,
        code_parts.get("html_code", ""),
        code_parts.get("css_code", ""),
        code_parts.get("js_code", ""),
    )


def render_codepen_snapshot_markdown(snapshot: CodePenSnapshot) -> str:
    lines = [
        "## CodePen Snapshot",
        "",
        f"Capture status: {snapshot.status}",
        f"Title: {snapshot.title or 'unknown'}",
        f"Author: {snapshot.author or 'unknown'}",
    ]
    if snapshot.description:
        lines.extend(["", "### Description / Embed Metadata", "", snapshot.description])
    if snapshot.reason:
        lines.extend(["", "### Blocked Reason", "", snapshot.reason])
    for label, code in (("HTML", snapshot.html_code), ("CSS", snapshot.css_code), ("JS", snapshot.js_code)):
        if not code:
            continue
        fence = "html" if label == "HTML" else label.lower()
        lines.extend(["", f"### {label}", "", f"```{fence}", markdown_fence_text(code), "```"])
    return "\n".join(lines).strip() + "\n"
