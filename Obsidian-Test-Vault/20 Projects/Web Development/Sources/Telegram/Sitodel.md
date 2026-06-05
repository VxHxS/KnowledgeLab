---
type: telegram_source
scope: web
project: web-development
source: telegram
source_url: "https://t.me/sitodel"
chat_name: "sitodel"
ad_filter: separate
status: queued
tags: [project/web-development, source/telegram, source/sitodel]
---

# Telegram · sitodel

URL: https://t.me/sitodel

## Зачем добавлен

Telegram-источник с хорошими web-решениями.

## Импорт

1. Открыть канал/чат в Telegram Desktop.
2. Export chat history -> Machine-readable JSON.
3. Указать `result.json` в desktop importer.
4. Для scope выбрать `web`.
5. Для рекламы использовать режим `separate`, чтобы подозрительные сообщения уходили в отдельную папку и не попадали в LightRAG index.

## Команда

```powershell
.\LightRAG\.venv\Scripts\python.exe scripts\import-telegram-export.py --input "C:\path\to\result.json" --chat-name "sitodel" --scope web --project web-development --out-dir "20 Projects/Web Development/Sources/Telegram" --ad-filter separate
```

