from __future__ import annotations

import json
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


def _is_ddg_internal_url(url: str) -> bool:
    """Check if URL is a DuckDuckGo internal page (not a real search result)."""
    lower = url.lower()
    return "duckduckgo.com" in lower and not lower.endswith(".js")


def _dedupe_results(raw: list[dict[str, str]], max_results: int) -> list[dict[str, str]]:
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for result in raw:
        url = result.get("url", "").strip()
        title = result.get("title", "").strip()
        if not url or not title:
            continue
        if _is_ddg_internal_url(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        unique.append(result)
        if len(unique) >= max_results:
            break
    return unique


def _fetch_json_api(query: str, max_results: int, timeout: int) -> list[dict[str, str]]:
    """Try DuckDuckGo JSON API (more stable than HTML parsing)."""
    url = "https://api.duckduckgo.com/?" + urlencode({"q": query, "format": "json", "no_html": 1, "skip_disambig": 1})
    headers = {"User-Agent": "Mozilla/5.0 KnowledgeLab/1.0 (+local web context)"}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read(500_000).decode("utf-8", errors="replace"))
    except Exception:
        return []

    results: list[dict[str, str]] = []

    abstract = data.get("AbstractText", "")
    abstract_url = data.get("AbstractURL", "")
    if abstract and abstract_url:
        results.append({"url": abstract_url, "title": data.get("Heading", query), "snippet": abstract})

    for topic in data.get("RelatedTopics", []):
        if isinstance(topic, dict) and "Text" in topic:
            url = topic.get("FirstURL", "")
            text = topic.get("Text", "")
            if url and text:
                results.append({"url": url, "title": text[:120], "snippet": text})
        elif isinstance(topic, dict) and "Topics" in topic:
            for sub in topic["Topics"][:3]:
                if isinstance(sub, dict) and "Text" in sub:
                    url = sub.get("FirstURL", "")
                    text = sub.get("Text", "")
                    if url and text:
                        results.append({"url": url, "title": text[:120], "snippet": text})

    return _dedupe_results(results, max_results)


def _fetch_html(query: str, max_results: int, timeout: int) -> list[dict[str, str]]:
    """Fallback: parse DuckDuckGo HTML pages."""
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
        results = _dedupe_results(parser.results, max_results)
        if results:
            return results
    return []


def fetch_web_search_results(query: str, *, max_results: int = 5, timeout: int = 12) -> list[dict[str, str]]:
    """Fetch search results from DuckDuckGo. Tries JSON API first, then HTML fallback."""
    results = _fetch_json_api(query, max_results, timeout)
    if results:
        return results
    return _fetch_html(query, max_results, timeout)


def render_web_search_context(query: str, results: list[dict[str, str]]) -> str:
    """Render search results as a clear context block for the LLM."""
    lines = [
        "=== Web search context ===",
        f"Query: {query}",
        f"Results found: {len(results)}",
        "",
        "These are REAL search results from the internet. USE THEM to answer the question.",
        "Do NOT invent or make up answers. If results are relevant, summarize them clearly.",
        "If results are not relevant to the question, say so honestly.",
        "Always cite source URLs when using search results.",
        "",
    ]
    for index, result in enumerate(results, 1):
        title = result.get("title", "").strip()
        url = result.get("url", "").strip()
        snippet = result.get("snippet", "").strip()
        lines.append(f"[{index}] {title}")
        lines.append(f"    URL: {url}")
        if snippet:
            lines.append(f"    {snippet}")
        lines.append("")
    lines.append("=== End of web search context ===")
    return "\n".join(lines)
