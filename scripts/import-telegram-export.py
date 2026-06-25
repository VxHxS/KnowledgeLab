from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from knowledgelab.config import ROOT, VAULT_DIR
from knowledgelab.utils.text import clean_filename, yaml_quote
from knowledgelab.utils.urls import URL_RE
from vault_sources import slugify
AD_NOISE_PATTERNS: list[tuple[str, str, int]] = [
    ("explicit_ad", r"(?i)(#\s*реклама|\bреклам[ауыо]?|\bad\b|\bads\b|sponsored|спонсорск)", 4),
    ("promo_offer", r"(?i)(промокод|скидк|акци[яи]|распродаж|sale|discount|special offer)", 2),
    ("purchase_cta", r"(?i)(купить|заказать|оплатить|цена|стоимость|руб\.?|₽|\$|доступ к|оформить)", 2),
    ("lead_magnet", r"(?i)(бесплатн[а-я]* вебинар|марафон|интенсив|разбор|созвон|консультац)", 1),
    ("subscribe_cta", r"(?i)(подписывай|подписаться|переходи|жми|успей|оставь заявку|регистрац)", 1),
    ("channel_promo", r"(?i)(наш канал|мой канал|чат-бот|боте|партнерск|affiliate|реферальн)", 1),
]


def flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = str(item.get("text", ""))
                href = item.get("href")
                if href and text and href != text:
                    parts.append(f"{text} ({href})")
                else:
                    parts.append(text)
        return "".join(parts)
    return str(value)


def message_datetime(message: dict[str, Any]) -> dt.datetime:
    raw = str(message.get("date") or message.get("date_unixtime") or "")
    if raw.isdigit():
        return dt.datetime.fromtimestamp(int(raw), tz=dt.timezone.utc).replace(tzinfo=None)
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return dt.datetime.now().replace(microsecond=0)


def extract_links(message: dict[str, Any], text: str) -> list[str]:
    links = set(URL_RE.findall(text))
    for field in ("text_entities", "caption_entities"):
        for entity in message.get(field, []) or []:
            if isinstance(entity, dict):
                href = entity.get("href")
                entity_text = entity.get("text")
                if href:
                    links.add(str(href))
                if isinstance(entity_text, str):
                    links.update(URL_RE.findall(entity_text))
    return sorted(links)


def message_text(message: dict[str, Any]) -> str:
    text = flatten_text(message.get("text"))
    caption = flatten_text(message.get("caption"))
    if caption and caption not in text:
        text = f"{text}\n\n{caption}".strip()
    return text


def classify_ad_noise(message: dict[str, Any]) -> dict[str, Any]:
    text = message_text(message)
    links = extract_links(message, text)
    score = 0
    reasons: list[str] = []

    for reason, pattern, weight in AD_NOISE_PATTERNS:
        if re.search(pattern, text):
            score += weight
            reasons.append(reason)

    if len(links) >= 3:
        score += 2
        reasons.append("many_links")
    elif len(links) >= 2 and len(text) < 500:
        score += 1
        reasons.append("short_multi_link")

    if links and len(text) < 120:
        score += 1
        reasons.append("short_link_post")

    if message.get("forwarded_from") and score >= 2:
        score += 1
        reasons.append("forwarded_promo_shape")

    return {
        "is_noise": score >= 4,
        "score": score,
        "reasons": list(dict.fromkeys(reasons)),
    }


def media_lines(message: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ("photo", "file", "thumbnail"):
        value = message.get(key)
        if value:
            lines.append(f"- {key}: `{value}`")
    media_type = message.get("media_type")
    if media_type:
        lines.insert(0, f"- media_type: `{media_type}`")
    return lines


def render_message(message: dict[str, Any], ad_info: dict[str, Any] | None = None) -> str:
    msg_id = message.get("id", "")
    when = message_datetime(message)
    author = message.get("from") or message.get("actor") or message.get("from_id") or "unknown"
    text = message_text(message)
    links = extract_links(message, text)
    media = media_lines(message)

    lines = [
        f"## {when:%Y-%m-%d %H:%M} · message {msg_id}",
        "",
        f"- author: {author}",
    ]
    if message.get("reply_to_message_id"):
        lines.append(f"- reply_to_message_id: {message.get('reply_to_message_id')}")
    if message.get("forwarded_from"):
        lines.append(f"- forwarded_from: {message.get('forwarded_from')}")
    if ad_info and ad_info.get("is_noise"):
        reasons = ", ".join(str(reason) for reason in ad_info.get("reasons", []))
        lines.append("- ad_noise_candidate: true")
        lines.append(f"- ad_noise_score: {ad_info.get('score', 0)}")
        if reasons:
            lines.append(f"- ad_noise_reasons: {reasons}")
    lines.append("")

    if text:
        lines.extend([text.strip(), ""])
    if links:
        lines.extend(["### Links", *[f"- {link}" for link in links], ""])
    if media:
        lines.extend(["### Media", *media, ""])
    return "\n".join(lines).rstrip() + "\n"


def load_export(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Telegram Desktop JSON export to Obsidian Markdown."
    )
    parser.add_argument("--input", required=True, help="Path to Telegram Desktop result.json")
    parser.add_argument("--chat-name", default="", help="Override chat/channel name")
    parser.add_argument("--scope", default="general", choices=["general", "game", "web", "all"])
    parser.add_argument("--project", default="", help="Project id, for example my-game or web-development")
    parser.add_argument(
        "--out-dir",
        default="30 Sources/Telegram",
        help="Output folder inside the Obsidian vault",
    )
    parser.add_argument(
        "--vault-dir",
        default=str(VAULT_DIR),
        help="Obsidian vault folder. Defaults to the project test vault.",
    )
    parser.add_argument(
        "--one-file",
        action="store_true",
        help="Write one Markdown file instead of monthly files",
    )
    parser.add_argument(
        "--ad-filter",
        default="mark",
        choices=["off", "mark", "separate", "skip"],
        help=(
            "Ad/noise handling: off imports as-is; mark annotates suspicious messages; "
            "separate writes them into lightrag_exclude files; skip drops them from output."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    vault_dir = Path(args.vault_dir).expanduser().resolve()
    data = load_export(input_path)
    chat_name = args.chat_name or data.get("name") or input_path.parent.name
    chat_slug = slugify(chat_name)
    output_root = vault_dir / args.out_dir / clean_filename(chat_name)
    output_root.mkdir(parents=True, exist_ok=True)

    messages = [
        message
        for message in data.get("messages", [])
        if isinstance(message, dict) and message.get("type") == "message"
    ]

    buckets: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    ad_buckets: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    filtered_count = 0
    skipped_count = 0
    for message in messages:
        when = message_datetime(message)
        key = "all" if args.one_file else f"{when:%Y-%m}"
        ad_info = {"is_noise": False, "score": 0, "reasons": []}
        if args.ad_filter != "off":
            ad_info = classify_ad_noise(message)

        if ad_info.get("is_noise") and args.ad_filter == "skip":
            skipped_count += 1
            continue
        if ad_info.get("is_noise") and args.ad_filter == "separate":
            filtered_count += 1
            ad_buckets[key].append((message, ad_info))
            continue
        if ad_info.get("is_noise"):
            filtered_count += 1
        buckets[key].append((message, ad_info))

    imported_at = dt.datetime.now().replace(microsecond=0).isoformat()
    written: list[Path] = []
    ad_written: list[Path] = []

    def write_bucket_file(
        file_path: Path,
        title_suffix: str,
        bucket: list[tuple[dict[str, Any], dict[str, Any]]],
        *,
        exclude_from_lightrag: bool,
        filtered_ads_file: bool,
    ) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        tags = ["source/telegram", "imported/telegram"]
        if filtered_ads_file:
            tags.append("filtered/ad-noise")

        frontmatter = [
            "---",
            "type: telegram_export",
            "source: telegram",
            f"chat: {yaml_quote(chat_name)}",
            f"chat_id: {yaml_quote(str(data.get('id', '')))}",
            f"scope: {args.scope}",
            f"project: {yaml_quote(args.project)}",
            f"telegram_export: {yaml_quote(str(input_path))}",
            f"imported_at: {yaml_quote(imported_at)}",
            f"ad_filter: {args.ad_filter}",
        ]
        if exclude_from_lightrag:
            frontmatter.append("lightrag_exclude: true")
        frontmatter.extend([
            f"tags: [{', '.join(tags)}]",
            "---",
            "",
        ])
        heading = "Telegram filtered ads/noise" if filtered_ads_file else "Telegram"
        body = [
            f"# {heading} · {chat_name} · {title_suffix}",
            "",
            f"Imported messages: {len(bucket)}",
            "",
        ]
        for message, ad_info in bucket:
            body.append(render_message(message, ad_info))

        file_path.write_text(
            "\n".join(frontmatter + body).rstrip() + "\n",
            encoding="utf-8-sig",
        )

    for key, bucket in sorted(buckets.items()):
        title_suffix = "all" if key == "all" else key
        file_path = output_root / f"{title_suffix}.md"
        write_bucket_file(
            file_path,
            title_suffix,
            bucket,
            exclude_from_lightrag=False,
            filtered_ads_file=False,
        )
        written.append(file_path)

    for key, bucket in sorted(ad_buckets.items()):
        title_suffix = "all" if key == "all" else key
        file_path = output_root / "Filtered Ads" / f"{title_suffix}.md"
        write_bucket_file(
            file_path,
            title_suffix,
            bucket,
            exclude_from_lightrag=True,
            filtered_ads_file=True,
        )
        ad_written.append(file_path)

    print(f"Imported {len(messages)} Telegram messages from {input_path}")
    print(f"Ad filter: {args.ad_filter}")
    if filtered_count:
        print(f"Ad/noise candidates: {filtered_count}")
    if skipped_count:
        print(f"Skipped ad/noise candidates: {skipped_count}")
    for path in written:
        print(f"- {path.relative_to(vault_dir).as_posix()}")
    for path in ad_written:
        print(f"- {path.relative_to(vault_dir).as_posix()} [excluded from LightRAG]")


if __name__ == "__main__":
    main()
