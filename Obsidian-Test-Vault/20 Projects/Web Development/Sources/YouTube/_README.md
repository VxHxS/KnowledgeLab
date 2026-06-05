---
type: source_folder
scope: web
project: web-development
source: youtube
tags: [project/web-development, source/youtube]
---

# Web YouTube Sources

Для добавления видео создай заметку со ссылкой и frontmatter:

```yaml
---
type: youtube_link
source: youtube_link
source_url: "https://www.youtube.com/watch?v=..."
scope: web
project: web-development
area: web-development
topic:
tags: [project/web-development, source/youtube]
---
```

Синк транскриптов:

```powershell
.\LightRAG\.venv\Scripts\python.exe scripts\sync-youtube-links.py --scope web --project web-development
```

