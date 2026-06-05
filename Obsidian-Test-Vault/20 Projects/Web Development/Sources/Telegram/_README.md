---
type: source_folder
scope: web
project: web-development
source: telegram
tags: [project/web-development, source/telegram]
---

# Web Telegram Sources

Сюда импортируются Telegram Desktop JSON exports по web-разработке.

## Источники

- [[20 Projects/Web Development/Sources/Telegram/Sitodel]]
- [[20 Projects/Web Development/Sources/Telegram/Private Web Group]]

## Фильтр рекламы

Для публичных каналов с возможной рекламой лучше использовать режим `separate`: подозрительные сообщения сохраняются отдельно и получают `lightrag_exclude: true`, чтобы не засорять ответы.

Для личных групп безопаснее начинать с `mark`: сообщения остаются в основном файле, но помечаются `ad_noise_candidate`.

Ручной запуск:

```powershell
.\LightRAG\.venv\Scripts\python.exe scripts\import-telegram-export.py --input "C:\path\to\result.json" --chat-name "Web группа" --scope web --project web-development --out-dir "20 Projects/Web Development/Sources/Telegram" --ad-filter separate
```
