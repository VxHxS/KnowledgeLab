from __future__ import annotations

import html
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from knowledgelab.config import (
    ARTICLE_FALLBACK_MIN_CHARS,
    ARTICLE_TEXT_EXTRACTION_LIMIT,
    REFERENCE_LINK_HINTS,
    REFERENCE_LINK_LIMIT,
)
from knowledgelab.models import ReferenceLink
from knowledgelab.utils.text import (
    clean_filename,
    compact_whitespace,
    markdown_fence_text,
)
from knowledgelab.utils.urls import (
    URL_RE,
    first_url,
    normalize_source_url_for_match,
    parse_codepen_url,
    parse_github_url,
    source_domain,
)


def title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip().strip("#").strip()
        if line and not URL_RE.fullmatch(line):
            return clean_filename(line)
    url = first_url(text)
    if url:
        return clean_filename(url.replace("https://", "").replace("http://", ""))
    return fallback


class ArticleTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.parts: list[str] = []
        self.current_tag = ""
        self.skip_depth = 0
        self.title_active = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas", "form", "nav", "footer", "header"}:
            self.skip_depth += 1
            return
        if tag == "title":
            self.title_active = True
        if tag in {"p", "li", "h1", "h2", "h3", "pre", "code", "blockquote"}:
            self.current_tag = tag

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip_depth:
            if tag in {"script", "style", "noscript", "svg", "canvas", "form", "nav", "footer", "header"}:
                self.skip_depth -= 1
            return
        if tag == "title":
            self.title_active = False
            self.title = compact_whitespace(" ".join(self.title_parts))[:180]
        if tag in {"p", "li", "h1", "h2", "h3", "pre", "blockquote"}:
            self.parts.append("\n")
            self.current_tag = ""

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = compact_whitespace(data)
        if not text:
            return
        if self.title_active:
            self.title_parts.append(text)
            return
        if self.current_tag:
            if self.current_tag == "li":
                text = f"- {text}"
            if self.current_tag in {"h1", "h2", "h3"}:
                text = f"## {text}"
            self.parts.append(text)

    def markdown(self) -> str:
        lines: list[str] = []
        previous_blank = True
        for part in self.parts:
            text = part.strip()
            if not text:
                if not previous_blank:
                    lines.append("")
                previous_blank = True
                continue
            lines.append(text)
            previous_blank = False
        return "\n".join(lines).strip()


class VisiblePageTextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "form", "template", "nav", "footer", "header"}
    BLOCK_TAGS = {
        "article", "main", "section", "div", "p", "li", "ul", "ol", "blockquote",
        "pre", "table", "tr", "td", "th", "br",
    }
    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    META_KEYS = {"description", "og:description", "twitter:description", "og:title", "twitter:title"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.parts: list[str] = []
        self.meta_parts: list[str] = []
        self.title_active = False
        self.title_parts: list[str] = []
        self.head_depth = 0
        self.skip_depth = 0
        self.current_heading = ""
        self.li_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        attrs_dict = {name.lower(): value or "" for name, value in attrs}
        if self.skip_depth:
            self.skip_depth += 1
            return
        if tag == "head":
            self.head_depth += 1
            return
        if tag == "title":
            self.title_active = True
            return
        if tag == "meta":
            key = (attrs_dict.get("name") or attrs_dict.get("property") or "").strip().lower()
            content = compact_whitespace(attrs_dict.get("content", ""))
            if key in self.META_KEYS and content:
                self.meta_parts.append(content)
            return
        if tag in self.SKIP_TAGS or attrs_dict.get("hidden") is not None or attrs_dict.get("aria-hidden", "").lower() == "true":
            self.skip_depth += 1
            return
        if self.head_depth:
            return
        if tag in self.HEADING_TAGS:
            self.current_heading = tag
            self.parts.append("\n")
        elif tag == "li":
            self.li_depth += 1
            self.parts.append("\n")
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "meta":
            self.handle_starttag(tag, attrs)
        elif tag == "br" and not self.skip_depth and not self.head_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip_depth:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if tag == "head":
            self.head_depth = max(0, self.head_depth - 1)
            return
        if tag == "title":
            self.title_active = False
            self.title = compact_whitespace(" ".join(self.title_parts))[:180]
            return
        if self.head_depth:
            return
        if tag in self.HEADING_TAGS:
            self.current_heading = ""
            self.parts.append("\n")
        elif tag == "li":
            self.li_depth = max(0, self.li_depth - 1)
            self.parts.append("\n")
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = compact_whitespace(data)
        if not text:
            return
        if self.title_active:
            self.title_parts.append(text)
            return
        if self.head_depth:
            return
        if self.current_heading:
            self.parts.append(f"## {text}")
        elif self.li_depth:
            self.parts.append(f"- {text}")
        else:
            self.parts.append(text)

    def markdown(self) -> str:
        lines: list[str] = []
        previous_blank = True
        for part in self.meta_parts + self.parts:
            text = part.strip()
            if not text:
                if not previous_blank:
                    lines.append("")
                previous_blank = True
                continue
            lines.append(text)
            previous_blank = False
        return "\n".join(lines).strip()


class ScriptAssetExtractor(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.page_host = urlparse(page_url).netloc.lower()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "script":
            return
        attrs_dict = {name.lower(): value or "" for name, value in attrs}
        src = attrs_dict.get("src", "").strip()
        if not src:
            return
        absolute = urljoin(self.page_url, src)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != self.page_host:
            return
        if not parsed.path.lower().endswith(".js"):
            return
        if absolute not in self.urls:
            self.urls.append(absolute)


class ReferenceLinkExtractor(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.current: dict[str, str | list[str]] | None = None
        self.links: list[ReferenceLink] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {name.lower(): value or "" for name, value in attrs}
        href = attrs_dict.get("href", "").strip()
        if not href:
            return
        absolute = urljoin(self.page_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            return
        self.current = {
            "url": absolute.rstrip("/"),
            "title": attrs_dict.get("title", "").strip(),
            "class": attrs_dict.get("class", "").strip(),
            "text": [],
        }

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            cast_list = self.current.get("text")
            if isinstance(cast_list, list):
                cast_list.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            self.flush()

    def close(self) -> None:
        self.flush()
        super().close()

    def flush(self) -> None:
        if self.current is None:
            return
        text_parts = self.current.get("text")
        text = compact_whitespace(" ".join(text_parts if isinstance(text_parts, list) else []))
        title = compact_whitespace(str(self.current.get("title") or "") or text)
        context = compact_whitespace(" ".join(part for part in (title, text, str(self.current.get("class") or "")) if part))
        url = str(self.current.get("url") or "")
        role = classify_reference_link_role(url, context, self.page_url)
        if role:
            self.links.append(ReferenceLink(url=url, title=title or url, context=context[:420], role=role))
        self.current = None


def classify_reference_link_role(url: str, context: str, parent_url: str = "") -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    parent_host = urlparse(parent_url).netloc.lower().removeprefix("www.") if parent_url else ""
    seed = f"{host} {parsed.path} {context}".lower()
    if host == "codepen.io" and parse_codepen_url(url):
        return "codepen_pen"
    if host == "github.com" and parse_github_url(url):
        return "github_repository"
    if any(hint in seed for hint in REFERENCE_LINK_HINTS):
        return "example_reference"
    if host and parent_host and host != parent_host and context:
        return "external_reference"
    return ""


def extract_reference_links_from_html(html_text: str, page_url: str, limit: int = REFERENCE_LINK_LIMIT) -> list[ReferenceLink]:
    parser = ReferenceLinkExtractor(page_url)
    parser.feed(html_text)
    parser.close()
    seen: set[str] = set()
    links: list[ReferenceLink] = []
    parent_normalized = normalize_source_url_for_match(page_url)
    for link in parser.links:
        normalized = normalize_source_url_for_match(link.url)
        if not normalized or normalized == parent_normalized or normalized in seen:
            continue
        seen.add(normalized)
        links.append(link)
        if len(links) >= limit:
            break
    return links


def dedupe_markdown_lines(markdown: str) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    previous_blank = True
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        normalized = compact_whitespace(line).lower()
        if not normalized:
            if not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        if len(normalized) >= 16:
            if normalized in seen:
                continue
            seen.add(normalized)
        lines.append(line)
        previous_blank = False
    return "\n".join(lines).strip()


def extract_article_markdown_from_html(html: str, url: str) -> tuple[str, str]:
    extractor = ArticleTextExtractor()
    extractor.feed(html)
    title = extractor.title
    markdown = dedupe_markdown_lines(extractor.markdown())
    if len(compact_whitespace(markdown)) < ARTICLE_FALLBACK_MIN_CHARS:
        fallback = VisiblePageTextExtractor()
        fallback.feed(html)
        fallback_markdown = dedupe_markdown_lines(fallback.markdown())
        if len(compact_whitespace(fallback_markdown)) > len(compact_whitespace(markdown)):
            markdown = fallback_markdown
        title = title or fallback.title
    title = title or title_from_text(url, "Web article")
    return title, markdown[:ARTICLE_TEXT_EXTRACTION_LIMIT]


JS_STRING_RE = re.compile(r"([\"'`])((?:\\.|(?!\1).)*?)\1", re.DOTALL)


def decode_js_string(value: str) -> str:
    def replace_unicode(match: re.Match[str]) -> str:
        try:
            return chr(int(match.group(1), 16))
        except ValueError:
            return ""

    value = re.sub(r"\\u([0-9a-fA-F]{4})", replace_unicode, value)
    value = (
        value.replace("\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\t", " ")
        .replace('\\"', '"')
        .replace("\\'", "'")
        .replace("\\`", "`")
        .replace("\\/", "/")
        .replace("\\\\", "\\")
    )
    return html.unescape(compact_whitespace(value))


def is_human_js_text(value: str) -> bool:
    if len(value) < 3 or len(value) > 420:
        return False
    if not re.search(r"[A-Za-zА-Яа-яЁё]", value):
        return False
    has_cyrillic = bool(re.search(r"[А-Яа-яЁё]", value))
    if not has_cyrillic and " " not in value:
        return False
    if not has_cyrillic and len(value.split()) > 5 and value == value.lower():
        return False
    lower = value.lower()
    exact_bad = {
        "; visit", "at new", "invariant violation", "request aborted", "network error",
        "timeout exceeded", "unsupported protocol", "unknown option", "project image",
        "relative z-0", "must be", "since :", "has been removed",
    }
    if lower in exact_bad:
        return False
    bad_fragments = (
        "modulepreload", "function", "prototype", "object", "symbol.", "exports", "import.meta",
        "react.production", "minified react", "non-minified dev", "mutationobserver", "react.cloneelement",
        "document.", "window.", "children", "classname", "onclick", "onpointer", "onmouse",
        "aria-", "xmlns", "www.w3.org", "data:image", "base64", "new url", "assets/",
        "use strict", "sourcemappingurl", "prefers-reduced-motion", "forceframerate",
        "full message", "history only accepts", "cannot include", "unknown-event",
        "dangerouslysetinnerhtml", "suppresscontenteditablewarning", "suppresshydrationwarning",
        "window.location", "active listener", "production builds of react", "allowfullscreen",
        "mousedown mouseup", "error generating stack", "router will parse", "prop-types",
        "blob is not supported", "circular reference", "request failed", "timeout of",
        "ms exceeded", "adapter specified", "suitable adapter", "deprecated since",
        "alternatively you may provide", "max-width:", "pointer:", "read-only method",
        "response from server:",
    )
    if any(fragment in lower for fragment in bad_fragments):
        return False
    if re.search(r"\.(?:js|css|png|jpe?g|svg|gif|webp|glb|gltf|woff2?|ttf)\b", lower):
        return False
    if any(marker in value for marker in ("=>", "{", "}", "&&", "||")):
        return False
    if re.fullmatch(r"[0-9.%-]+(?:px|em|rem|vh|vw)?(?:\s+[0-9.%-]+(?:px|em|rem|vh|vw)?)*", lower):
        return False
    if re.fullmatch(r"[0-9.]+px\s+solid\s+#[0-9a-f]+", lower):
        return False
    if "[" in value or "]" in value:
        return False
    if re.search(r"(?:^|\s)(?:sm:|md:|lg:|xl:|2xl:|text-|bg-|px-|py-|mt-|mb-|w-|h-|flex|grid)\S*", lower):
        return False
    readable_chars = len(re.findall(r"[A-Za-zА-Яа-яЁё0-9\s.,:;!?()'\"№/%+-]", value))
    if readable_chars / max(len(value), 1) < 0.62:
        return False
    if " " not in value and len(value) > 32 and not re.search(r"[А-Яа-яЁё]", value):
        return False
    return True


def extract_human_strings_from_js(script_text: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for match in JS_STRING_RE.finditer(script_text):
        raw = match.group(2)
        if len(raw) > 600:
            continue
        value = decode_js_string(raw)
        if not is_human_js_text(value):
            continue
        normalized = compact_whitespace(value).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(value)
    return items


def extract_spa_bundle_markdown(
    html_text: str,
    page_url: str,
    *,
    timeout: int,
    limit_bytes: int,
    max_scripts: int = 4,
) -> str:
    parser = ScriptAssetExtractor(page_url)
    parser.feed(html_text)
    items: list[str] = []
    seen: set[str] = set()
    for script_url in parser.urls[:max_scripts]:
        try:
            request = urllib.request.Request(
                script_url,
                headers={"User-Agent": "KnowledgeLab/1.0 (+local Obsidian capture)"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(limit_bytes)
            script_text = raw.decode("utf-8", errors="replace")
        except Exception:
            continue
        for item in extract_human_strings_from_js(script_text):
            normalized = compact_whitespace(item).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            items.append(item)
            if len(items) >= 220:
                break
        if len(items) >= 220:
            break
    if not items:
        return ""
    return dedupe_markdown_lines("## SPA Bundle Text Snapshot\n\n" + "\n".join(f"- {item}" for item in items))


def fetch_article_material(url: str, *, timeout: int = 15, limit_bytes: int = 2_500_000) -> tuple[str, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KnowledgeLab/1.0 (+local Obsidian capture)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.2",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        raw = response.read(limit_bytes)
    charset_match = re.search(r"charset=([\w.-]+)", content_type, re.IGNORECASE)
    charset = charset_match.group(1) if charset_match else "utf-8"
    html_text = raw.decode(charset, errors="replace")
    if "text/plain" in content_type.lower():
        return title_from_text(url, "Web article"), dedupe_markdown_lines(html_text)[:ARTICLE_TEXT_EXTRACTION_LIMIT], html_text
    title, markdown = extract_article_markdown_from_html(html_text, url)
    if len(compact_whitespace(markdown)) < ARTICLE_FALLBACK_MIN_CHARS:
        spa_markdown = extract_spa_bundle_markdown(html_text, url, timeout=timeout, limit_bytes=limit_bytes)
        if spa_markdown:
            markdown = dedupe_markdown_lines("\n\n".join(part for part in (markdown, spa_markdown) if part))
    return title, markdown[:ARTICLE_TEXT_EXTRACTION_LIMIT], html_text


def fetch_article_markdown(url: str, *, timeout: int = 15, limit_bytes: int = 2_500_000) -> tuple[str, str]:
    title, markdown, _html = fetch_article_material(url, timeout=timeout, limit_bytes=limit_bytes)
    return title, markdown


def collect_local_folder_files(folder_path: "Path", *, scan_limit: int = 0) -> tuple[list["Path"], bool]:
    """Collect files from a local folder, respecting skip dirs and scan limits."""
    from pathlib import Path
    from knowledgelab.config import FOLDER_SKIP_DIRS, FOLDER_FILE_SCAN_LIMIT

    if scan_limit <= 0:
        scan_limit = FOLDER_FILE_SCAN_LIMIT
    files: list[Path] = []
    scan_complete = True
    try:
        for root, dirs, filenames in folder_path.walk():
            dirs[:] = [d for d in dirs if d not in FOLDER_SKIP_DIRS]
            for fname in filenames:
                fpath = Path(root) / fname
                files.append(fpath)
                if len(files) >= scan_limit:
                    scan_complete = False
                    return files, scan_complete
    except OSError:
        scan_complete = False
    return files, scan_complete


def summarize_local_folder(folder_path: "Path") -> tuple[str, str, dict]:
    """Summarize a local folder's contents for capture."""
    from pathlib import Path

    files, scan_complete = collect_local_folder_files(folder_path)
    if not files:
        return "", "empty", {"file_count": 0, "scan_complete": scan_complete}

    text_parts: list[str] = []
    for f in files[:50]:
        try:
            name = f.name
            size = f.stat().st_size
            text_parts.append(f"- {name} ({size} bytes)")
        except OSError:
            continue

    text = "\n".join(text_parts)
    status = "extracted" if scan_complete else "partial"
    stats = {"file_count": len(files), "scan_complete": scan_complete}
    return text, status, stats
