---
type: project
scope: web
project: web-development
area: web-development
tags: [project/web-development, area/web-development]
---

# Web Development

Локальный проект для web-разработки: готовые решения, паттерны, ссылки, видео, Telegram-группы, статьи и личные выводы.

## Как пользоваться

1. Быстрые идеи и ссылки складывать в [[20 Projects/Web Development/Capture Queue]].
2. Готовые решения оформлять в [[20 Projects/Web Development/Solutions/_README]].
3. YouTube-ссылки помечать `type: youtube_link` и `scope: web`.
4. Telegram JSON exports импортировать в [[20 Projects/Web Development/Sources/Telegram/_README]].
5. После добавления источников запускать web reindex или web chat.

## Папки

- [[20 Projects/Web Development/Solutions/_README]] - практические решения.
- [[20 Projects/Web Development/Topics/_README]] - темы и направления изучения.
- [[20 Projects/Web Development/Sources/_README]] - первоисточники.

## LightRAG

Этот проект индексируется отдельным scope:

```powershell
scripts\ingest-vault-scope-lmstudio.ps1 -Scope web -Project web-development
scripts\chat-vault-lmstudio.ps1 -Scope web -Project web-development
```

