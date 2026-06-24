from __future__ import annotations

import urllib.request
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse, urlencode

from knowledgelab.utils.text import compact_whitespace


class DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None
        self.capture_title = False
        self.capture_snippet = False
        self.title_parts: list[str] = []
        self.snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = {name: value or "" for name, value in attrs}
        classes = attrs_dict.get("class", "")
        if tag == "a" and ("result__a" in classes or "result-link" in classes):
            self.flush()
            self.current = {"url": normalize_search_url(attrs_dict.get("href", "")), "title": "", "snippet": ""}
            self.title_parts = []
            self.capture_title = True
        elif self.current is not None and ("result__snippet" in classes or "result-snippet" in classes):
            self.snippet_parts = []
            self.capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.capture_title:
            self.capture_title = False
            if self.current is not None:
                self.current["title"] = compact_whitespace(" ".join(self.title_parts))
        elif self.capture_snippet and tag in {"a", "div", "td"}:
            self.capture_snippet = False
            if self.current is not None:
                self.current["snippet"] = compact_whitespace(" ".join(self.snippet_parts))

    def handle_data(self, data: str) -> None:
        text = compact_whitespace(data)
        if not text:
            return
        if self.capture_title:
            self.title_parts.append(text)
        elif self.capture_snippet:
            self.snippet_parts.append(text)

    def flush(self) -> None:
        if self.current and self.current.get("title"):
            self.results.append(self.current)
        self.current = None

    def close(self) -> None:
        self.flush()
        super().close()


def normalize_search_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "uddg" in params and params["uddg"]:
        return unquote(params["uddg"][0])
    return url


def fetch_web_search_results(query: str, *, max_results: int = 5, timeout: int = 12) -> list[dict[str, str]]:
    search_urls = [
        "https://duckduckgo.com/html/?" + urlencode({"q": query}),
        "https://lite.duckduckgo.com/lite/?" + urlencode({"q": query}),
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 KnowledgeLab/1.0 (+local web context)",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.2",
    }
    for search_url in search_urls:
        request = urllib.request.Request(search_url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                html_text = response.read(1_200_000).decode("utf-8", errors="replace")
        except Exception:
            continue
        parser = DuckDuckGoResultParser()
        parser.feed(html_text)
        parser.close()
        unique: list[dict[str, str]] = []
        seen: set[str] = set()
        for result in parser.results:
            url = result.get("url", "")
            title = result.get("title", "")
            if not url or not title or url in seen:
                continue
            seen.add(url)
            unique.append(result)
            if len(unique) >= max_results:
                break
        if unique:
            return unique
    return []


def render_web_search_context(query: str, results: list[dict[str, str]]) -> str:
    lines = [
        "Web search context for the next answer.",
        "Use this external web context only when it is relevant. Cite URLs when relying on it.",
        f"Search query: {query}",
        "",
    ]
    for index, result in enumerate(results, 1):
        lines.append(f"[{index}] {result.get('title', '').strip()}")
        lines.append(f"URL: {result.get('url', '').strip()}")
        snippet = result.get("snippet", "").strip()
        if snippet:
            lines.append(f"Snippet: {snippet}")
        lines.append("")
    return "\n".join(lines).strip()
