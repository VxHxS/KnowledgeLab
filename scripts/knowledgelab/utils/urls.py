from __future__ import annotations

import hashlib
import re
from urllib.parse import unquote, urlparse

from knowledgelab.utils.text import compact_whitespace

URL_RE = re.compile(r"https?://[^\s<>)\]]+", re.IGNORECASE)
GITHUB_SHORT_RE = re.compile(r"(?<!://)(?:www\.)?github\.com/[^\s<>)\]]+", re.IGNORECASE)
YOUTUBE_RE = re.compile(r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s<>)\]]+|youtu\.be/[^\s<>)\]]+)", re.IGNORECASE)
TELEGRAM_RE = re.compile(r"https?://t\.me/[^\s<>)\]]+", re.IGNORECASE)
CODEPEN_RE = re.compile(r"https?://(?:www\.)?codepen\.io/[^/\s<>)\]]+/pen/[A-Za-z0-9_-]+", re.IGNORECASE)


def first_url(text: str) -> str:
    match = URL_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


def first_youtube_url(text: str) -> str:
    match = YOUTUBE_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


def first_telegram_url(text: str) -> str:
    match = TELEGRAM_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


def first_codepen_url(text: str) -> str:
    match = CODEPEN_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


def parse_codepen_url(url: str) -> dict[str, str]:
    match = CODEPEN_RE.search(url.strip())
    if not match:
        return {}
    parsed = urlparse(match.group(0))
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 3 or parts[1].lower() != "pen":
        return {}
    owner = parts[0].strip()
    pen_id = parts[2].strip()
    if not owner or not pen_id:
        return {}
    canonical = f"https://codepen.io/{owner}/pen/{pen_id}"
    return {
        "codepen_owner": owner,
        "codepen_id": pen_id,
        "codepen_url": canonical,
        "codepen_oembed_url": f"https://codepen.io/api/oembed?url={canonical}&format=json",
        "codepen_debug_url": f"https://codepen.io/{owner}/debug/{pen_id}",
    }


def source_domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def stable_content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def normalize_github_url(value: str) -> str:
    value = value.strip().rstrip(".,;)]}>\"'")
    if not value:
        return ""
    if value.lower().startswith("www.github.com/") or value.lower().startswith("github.com/"):
        value = f"https://{value}"
    return value


def parse_github_url(url: str) -> dict[str, str]:
    url = normalize_github_url(url)
    if not url:
        return {}
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in {"github.com", "www.github.com"}:
        return {}
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return {}
    owner = parts[0].strip()
    repo = re.sub(r"\.git$", "", parts[1].strip(), flags=re.IGNORECASE)
    if not owner or not repo:
        return {}
    metadata = {
        "github_owner": owner,
        "github_repo": repo,
        "github_full_name": f"{owner}/{repo}",
        "github_clone_url": f"https://github.com/{owner}/{repo}.git",
    }
    if len(parts) >= 3:
        metadata["github_path"] = "/".join(parts[2:])
    if len(parts) >= 4 and parts[2].lower() in {"tree", "blob"}:
        metadata["github_ref"] = parts[3]
        if len(parts) >= 5:
            metadata["github_subpath"] = "/".join(parts[4:])
    return metadata


def first_github_url(text: str) -> str:
    for match in URL_RE.finditer(text):
        candidate = normalize_github_url(match.group(0))
        if parse_github_url(candidate):
            return candidate
    for match in GITHUB_SHORT_RE.finditer(text):
        candidate = normalize_github_url(match.group(0))
        if parse_github_url(candidate):
            return candidate
    return ""


def video_source_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


def normalize_source_url_for_match(url: str) -> str:
    url = normalize_github_url(url).strip()
    if not url:
        return ""
    codepen_meta = parse_codepen_url(url)
    if codepen_meta:
        url = codepen_meta["codepen_url"]
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = unquote(parsed.path or "/")
    path = "" if path == "/" else path.rstrip("/")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{host}{path}{query}".lower()
