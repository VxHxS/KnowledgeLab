# Архитектура: Obsidian + LightRAG + LM Studio + Codex

> Актуальная короткая схема с Mermaid-диаграммами, Desktop layout и fallback-поведением вынесена в `ARCHITECTURE.md`.

## Роли компонентов

`Obsidian` - источник правды. Здесь лежат Markdown-заметки по проектам, темам и первоисточникам. Ссылки на YouTube, Telegram-материалы, статьи и личные заметки добавляются сюда.

`LightRAG` - слой индексации и поиска. Он читает Markdown, режет текст на chunks, строит сущности/связи/индексы и на вопрос подбирает релевантный контекст. LightRAG не "ускоряет нейросеть" напрямую; он уменьшает объем мусорного контекста и помогает локальной модели видеть именно те куски базы знаний, которые нужны для ответа.

`LM Studio` - локальный сервер моделей. Он поднимает OpenAI-compatible API на `http://127.0.0.1:1234/v1`, отдает embeddings через `nomic-embed` и генерирует ответы через `qwen/qwen3-14b`.

`Chat/RAG client` - слой, которого не хватает в обычном LM Studio Chat. Это скрипт или приложение, которое принимает вопрос, вызывает LightRAG, получает найденный контекст и отправляет его в LM Studio. Сейчас эту роль выполняют:

```text
scripts/knowledge_chat_gui.py
scripts/query-vault-scope-lmstudio.ps1
scripts/chat-vault-lmstudio.ps1
desktop-launchers/LightRAG-Chat.cmd
desktop-launchers/Ask-General-Knowledge.ps1
desktop-launchers/Ask-My-Game.ps1
```

Основной пользовательский вход - единый desktop GUI chat. В режиме `Auto` он выбирает context `general`, `web` или `game` по тексту сообщения. Кнопка `Save to Obsidian` сохраняет ссылку или заметку в подходящую тему vault с frontmatter.
Telegram-ссылки сохраняются как `telegram_source`, YouTube-ссылки как `youtube_link`.

`Codex` - инженерный помощник и автоматизатор. Он правит скрипты, документацию, проверяет цепочку, запускает тесты и помогает развивать систему. В runtime-цепочке вопроса Codex не обязателен: когда все настроено, пользователь работает через Obsidian, LightRAG-скрипты/чат и LM Studio.

## Поток данных

```text
Obsidian Markdown
  -> sync/import scripts
  -> LightRAG ingest
  -> LightRAG storage
  -> LightRAG query
  -> LM Studio embeddings + LLM
  -> answer with references
```

## Почему LM Studio Chat сам по себе не видит Obsidian

Обычный чат LM Studio отправляет сообщение напрямую в модель. Он не знает, где лежит Obsidian vault, не читает Markdown и не вызывает LightRAG storage. Поэтому для вопросов по базе знаний нужен RAG-клиент:

```text
вопрос -> LightRAG retrieval -> найденный контекст -> LM Studio -> ответ
```

Если писать прямо в LM Studio Chat без такого клиента, модель будет отвечать только из своих общих знаний и из текста, который вручную вставлен в окно чата.

## Scope и проекты

Система разделяет знания через frontmatter и папки:

```yaml
scope: general
```

для общей базы знаний, Unity, программирования, музыки, статей и источников.

```yaml
scope: game
project: my-game
```

для конкретного игрового проекта.

```yaml
scope: web
project: web-development
```

для базы web-разработки: решений, YouTube/Telegram источников, статей, snippets и заметок по frontend/backend workflow.

Если frontmatter нет, скрипты делают осторожный вывод по папке:

```text
10 Programming -> general
10 General Knowledge -> general
20 Music -> general
30 Sources -> general
20 Projects/Web Development -> web
20 Projects/<project> -> game
```

## Sources

`Sources` - это первоисточники внутри темы или проекта. Примеры:

```text
10 Programming/Zenject/Sources/YouTube
20 Projects/My Game/Sources/YouTube
20 Projects/Web Development/Sources/YouTube
20 Projects/Web Development/Sources/Telegram
20 Projects/Web Development/Sources/Articles
30 Sources/Telegram
30 Sources/Articles
```

В идеале источники сортируются автоматически по `scope`, `project`, `area`, `topic` и тегам. Если уверенности не хватает, следующим шагом можно добавить desktop-приложение, которое спрашивает, куда положить материал.

## Текущий рабочий режим

1. Добавить или отредактировать заметки в Obsidian.
2. Для YouTube создать marked link note с `source: youtube_link`.
3. Запустить reindex нужного scope:

```powershell
scripts\ingest-vault-scope-lmstudio.ps1 -Scope general
scripts\ingest-vault-scope-lmstudio.ps1 -Scope game -Project my-game
scripts\ingest-vault-scope-lmstudio.ps1 -Scope web -Project web-development
```

4. Задать вопрос:

```powershell
scripts\query-vault-scope-lmstudio.ps1 -Scope general "Что говорится про Zenject?"
scripts\query-vault-scope-lmstudio.ps1 -Scope game -Project my-game "Что известно по моей игре?"
scripts\query-vault-scope-lmstudio.ps1 -Scope web -Project web-development "Какие web-решения есть в базе?"
```

5. Для чатового режима:

```powershell
scripts\chat-vault-lmstudio.ps1 -Scope general
scripts\chat-vault-lmstudio.ps1 -Scope game -Project my-game
scripts\chat-vault-lmstudio.ps1 -Scope web -Project web-development
```

## Что автоматизировать дальше

- File watcher для Obsidian vault, чтобы новые YouTube link notes сами запускали sync.
- Очередь обработки для длинных видео и больших Telegram-экспортов.
- Desktop UI, который показывает найденные источники и спрашивает тему/проект только когда автоматика не уверена.
- Инкрементальный reindex, чтобы не прогонять всю большую базу заново.
- Улучшить Telegram ad/noise filter: после накопления реальных примеров из `Filtered Ads` подстроить правила или заменить эвристику LLM-классификацией.
