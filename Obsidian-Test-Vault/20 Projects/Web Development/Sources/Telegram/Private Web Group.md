---
type: telegram_source
scope: web
project: web-development
source: telegram
source_url: "https://t.me/+PdYPIgDc0bY4OGEy"
chat_name: "Private Web Group"
ad_filter: mark
status: queued
tags: [project/web-development, source/telegram, source/private-group]
---

# Telegram · Private Web Group

URL: https://t.me/+PdYPIgDc0bY4OGEy

## Зачем добавлен

Личная Telegram-группа с собранными материалами по web-разработке.

## Импорт

Для приватной группы нужен Telegram Desktop export `result.json`. По invite-ссылке система не получает историю сообщений сама.

Рекомендуемый режим фильтра:

- `mark` для личной группы, чтобы ничего случайно не потерять;
- `separate`, если в экспорте много рекламы или пересланных промо.

## Команда

```powershell
.\LightRAG\.venv\Scripts\python.exe scripts\import-telegram-export.py --input "C:\path\to\result.json" --chat-name "Private Web Group" --scope web --project web-development --out-dir "20 Projects/Web Development/Sources/Telegram" --ad-filter mark
```

