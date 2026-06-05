# LightRAG + Obsidian + LM Studio: handoff

Дата состояния: 2026-06-03.

Дополнение от 2026-06-05: добавлен отдельный Obsidian-проект и LightRAG scope для web-разработки.

Этот файл нужен, чтобы открыть новый чат с Codex и продолжить настройку без пересказа всей истории. В новом чате сначала покажи этот файл или скажи: "прочитай `SYSTEM_HANDOFF.md` в AI-Knowledge-Lab".

## Короткая цель

Нужна локальная система базы знаний:

- Obsidian хранит Markdown-заметки по разным проектам и темам.
- YouTube-ссылка добавляется в Obsidian, система сама получает transcript.
- LightRAG индексирует Markdown из Obsidian.
- LM Studio поднимает локальную LLM и embedding model.
- Пользователь нажимает desktop launcher и получает чат, который отвечает по Obsidian + LightRAG.

## Главные пути

Проект:

```text
C:\MyFiles\KnowledgeLab
```

Obsidian vault:

```text
C:\MyFiles\KnowledgeLab\Obsidian-Test-Vault
```

Web Development project:

```text
C:\MyFiles\KnowledgeLab\Obsidian-Test-Vault\20 Projects\Web Development
```

Desktop-папка:

```text
C:\Users\Юрий\Desktop\LightRag
```

Control app:

```text
C:\Users\Юрий\Desktop\LightRag\LightRAG-Control
```

LM Studio API:

```text
http://127.0.0.1:1234/v1
```

Python venv:

```text
C:\MyFiles\KnowledgeLab\LightRAG\.venv
```

## Архитектура

Obsidian - источник правды. Все знания добавляются в Markdown-заметки.

LightRAG - индекс и retrieval-слой. Он не ускоряет нейросеть напрямую, а помогает ей видеть только релевантные chunks, сущности и связи из базы знаний.

LM Studio - локальный сервер моделей. Сейчас используются:

```text
LLM: qwen/qwen3-14b
Embeddings: nomic-embed
```

Chat/RAG client - отдельный слой поверх LM Studio. Обычный Chat UI в LM Studio сам по себе не читает Obsidian и не вызывает LightRAG.

Codex - инженерный помощник. Он не нужен в runtime, но нужен для настройки, правки скриптов, проверки цепочки и развития автоматизации.

Web Development scope:

```text
scope: web
project: web-development
storage: LightRAG/rag_storage_web
```

Команды:

```powershell
scripts\ingest-vault-scope-lmstudio.ps1 -Scope web -Project web-development
scripts\query-vault-scope-lmstudio.ps1 -Scope web -Project web-development "Какие web-решения есть в базе?"
scripts\chat-vault-lmstudio.ps1 -Scope web -Project web-development
```

Поток:

```text
Obsidian Markdown
  -> sync/import scripts
  -> LightRAG ingest
  -> LightRAG storage
  -> LightRAG query/chat
  -> LM Studio embeddings + LLM
  -> answer with references
```

## Что уже сделано

### Installer

Добавлен Windows installer:

```text
Install AI Knowledge Lab.cmd
scripts/install_wizard_gui.py
scripts/install-knowledge-lab.ps1
requirements-core.txt
requirements-all.txt
```

`Install AI Knowledge Lab.cmd` запускает классический wizard GUI установщика. Если Python GUI недоступен, launcher откатывается к консольному `install-knowledge-lab.ps1`.

Он собирает системные характеристики, проверяет зависимости, создает venv при наличии Python 3.10+, устанавливает выбранные Python packages, копирует desktop launchers и пишет:

```text
INSTALL_REPORT.md
```

Dry-run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-knowledge-lab.ps1 -DryRun -SkipPythonPackages -NoDesktopLaunchers
```

В текущей проверке dry-run увидел существующий venv, Python imports, LM Studio CLI/API и Git. CIM/WMI в среде Codex был ограничен, поэтому installer умеет жить с частичными характеристиками и пишет `Unknown`, если RAM/GPU/disk недоступны.

LightRAG вынесен отдельным компонентом установщика:

```text
package: lightrag-hku
requirements: requirements-core.txt
GitHub: https://github.com/HKUDS/LightRAG
PyPI: https://pypi.org/project/lightrag-hku/
```

### LightRAG-Control relocation

Система перенесена в:

```text
C:\Users\Юрий\Desktop\LightRag\LightRAG-Control
```

Фикс был сделан через:

```text
Resolve-LightRAG-Paths.ps1
```

Он ищет canonical root:

```text
C:\MyFiles\KnowledgeLab
```

`C:\Users\Юрий\Desktop\LightRag\LightRAG-Control.cmd` запускает Control app из подпапки.

Smoke по Control ранее показывал:

```text
ScriptCount=8
CmdCount=8
```

Текущая важная мысль пользователя: `LightRAG-Control` должен быть приложением для проверки/обслуживания системы. Добавление новых YouTube-материалов должно идти через Obsidian, не через Control.

В Control уже убран старый YouTube import launcher. Но там все еще есть `05 Import Telegram Export.cmd`; если строго придерживаться "Control только проверяет", в следующем этапе лучше перенести Telegram import в отдельный launcher/app или убрать из Control.

### YouTube transcript automation

Добавлены:

```text
scripts/import-youtube-transcript.py
scripts/sync-youtube-links.py
requirements-youtube.txt
```

`yt-dlp` установлен в LightRAG venv:

```text
yt-dlp 2026.03.17
```

Сценарий:

1. Пользователь создает Obsidian note с YouTube-ссылкой.
2. Note помечается `type: youtube_link` или `source: youtube_link`.
3. `sync-youtube-links.py` находит ссылку.
4. `import-youtube-transcript.py` получает captions/auto captions через `yt-dlp`.
5. Transcript сохраняется в Obsidian рядом с темой или проектом.
6. Reindex делает transcript доступным LightRAG.

Пример note-ссылки:

```text
Obsidian-Test-Vault/00 Inbox/Zenject Favorite Video.md
```

Содержит ссылку:

```text
https://www.youtube.com/watch?v=mbuzSrKHBHI&t=6802s
```

Frontmatter:

```yaml
---
type: youtube_link
source: youtube_link
source_url: "https://www.youtube.com/watch?v=mbuzSrKHBHI&t=6802s"
scope: general
project: ""
area: programming
topic: Zenject
favorite: true
tags: [source/youtube, topic/zenject, topic/unity]
---
```

Автоматический маршрут:

```text
10 Programming/Zenject/Sources/YouTube
```

Transcript-файл:

```text
Obsidian-Test-Vault/10 Programming/Zenject/Sources/YouTube/DI + UNITY = ZENJECT ⚡️ Dependency injection в Unity [mbuzSrKHBHI].md
```

Проверенный transcript:

```text
source: youtube
video_id: mbuzSrKHBHI
channel: K-Syndicate
language: ru-orig
transcript_method: auto_captions
chars: ~111946
```

Проверка sync:

```powershell
.\LightRAG\.venv\Scripts\python.exe scripts\sync-youtube-links.py --scope general --list-only
```

Ожидаемый результат:

```text
https://www.youtube.com/watch?v=mbuzSrKHBHI&t=6802s [general] 00 Inbox/Zenject Favorite Video.md -> 10 Programming/Zenject/Sources/YouTube
```

Повторный sync без `--overwrite` не дублирует:

```text
Already synced YouTube transcript: https://www.youtube.com/watch?v=mbuzSrKHBHI&t=6802s
Destination: 10 Programming/Zenject/Sources/YouTube
```

### LightRAG storage and checks

Полный `general` storage пока НЕ построен.

Существующие проверенные storages:

```text
LightRAG/rag_storage_zenject_test
LightRAG/rag_storage_game_my-game
```

`rag_storage_zenject_test` содержит 2 docs:

```text
00 Inbox/Zenject Favorite Video.md
10 Programming/Zenject/Sources/YouTube/DI + UNITY = ZENJECT ⚡️ Dependency injection в Unity [mbuzSrKHBHI].md
```

Проверка Zenject:

```powershell
$env:PYTHONUTF8="1"
$env:LMSTUDIO_RAG_DIR="LightRAG\rag_storage_zenject_test"
.\LightRAG\.venv\Scripts\python.exe scripts\query-vault-lmstudio.py "Что в видео говорится про dependency injection в Unity и Zenject? Укажи references."
```

Успешный результат:

```text
Loaded graph ... with 58 nodes, 52 edges
Naive query: 5 chunks
Final context: 4 chunks
References:
- 10 Programming/Zenject/Sources/YouTube/DI + UNITY = ZENJECT ⚡️ Dependency injection в Unity [mbuzSrKHBHI].md
```

`query-vault-lmstudio.py` был поправлен:

```text
LMSTUDIO_QUERY_MAX_TOTAL_TOKENS default = 12000
```

Причина: при старом лимите 2600 длинный transcript мог давать `Final context: 0 chunks`.

### Project scope

Починен файл:

```text
Obsidian-Test-Vault/20 Projects/My Game/_README.md
```

Frontmatter:

```yaml
---
type: project
scope: game
project: my-game
tags: [project/my-game]
---
```

Создан и проверен storage:

```text
LightRAG/rag_storage_game_my-game
```

Reindex:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ingest-vault-scope-lmstudio.ps1 -Scope game -Project my-game
```

Успешный результат:

```text
Writing graph with 2 nodes, 1 edges
Done. Indexed 1 Markdown files with LM Studio.
```

Query:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\query-vault-scope-lmstudio.ps1 -Scope game -Project my-game "Что сейчас известно по проекту my-game? Укажи references."
```

Успешный result:

```text
References:
- 20 Projects/My Game/_README.md
```

### Ask script

`scripts/ask-vault-lmstudio.ps1` раньше вызывал:

```text
simple-vault-rag-lmstudio.py
```

Теперь он вызывает:

```text
query-vault-scope-lmstudio.ps1
```

То есть desktop Ask-кнопки идут через настоящий LightRAG storage.

Default scope теперь:

```text
general
```

Если storage не найден, скрипт не падает глубоко в Python, а показывает:

```text
LightRAG storage was not found for scope 'general'.
Run first: scripts\ingest-vault-scope-lmstudio.ps1 -Scope general
```

### Chat layer

Создан чатовый слой:

```text
scripts/knowledge_chat_gui.py
scripts/chat-vault-lmstudio.py
scripts/chat-vault-lmstudio.ps1
```

Это НЕ встроенный чат LM Studio. Это отдельный RAG-чат:

```text
You -> LightRAG -> LM Studio -> Assistant with references
```

Преимущество `chat-vault-lmstudio.py`: он поднимает LightRAG storage один раз и дальше принимает несколько вопросов в одном окне.

Главный пользовательский launcher теперь:

```text
desktop-launchers/LightRAG-Chat.cmd
```

Он запускает GUI:

```text
desktop-launchers/LightRAG-Desktop-Chat.cmd
desktop-launchers/LightRAG-Desktop-Chat.ps1
```

GUI имеет один чат с режимом `Auto`. Он маршрутизирует вопросы в `general`, `web` или `game`, а кнопка `Добавить в Obsidian` раскладывает текущий текст/ссылку из поля ввода по vault. Это создание Markdown-заметки, не сохранение истории чата. Для YouTube создается `type: youtube_link`, чтобы последующий sync получил transcript.
Для `t.me/...` создается `type: telegram_source`.

Проверенный запуск:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\chat-vault-lmstudio.ps1 -Scope game -Project my-game
```

### Web Development project

Создан Obsidian-проект:

```text
Obsidian-Test-Vault/20 Projects/Web Development
```

Основные папки:

```text
Solutions
Topics
Sources/YouTube
Sources/Telegram
Sources/Articles
```

Добавлены шаблоны:

```text
Obsidian-Test-Vault/_Templates/Web Solution.md
Obsidian-Test-Vault/_Templates/Web YouTube Link.md
Obsidian-Test-Vault/_Templates/Web Article.md
```

Скрипты расширены на `web`:

```text
scripts/vault_sources.py
scripts/sync-youtube-links.py
scripts/import-youtube-transcript.py
scripts/import-telegram-export.py
scripts/ingest-vault-scope-lmstudio.ps1
scripts/query-vault-scope-lmstudio.ps1
scripts/chat-vault-lmstudio.ps1
scripts/ask-vault-lmstudio.ps1
```

Добавлены launchers:

```text
desktop-launchers/09 Ask Web Development.cmd
desktop-launchers/Ask-Web-Development.ps1
desktop-launchers/LightRAG-Desktop-Chat.cmd
desktop-launchers/LightRAG-Desktop-Chat.ps1
desktop-launchers/LightRAG-Web-Chat.cmd
desktop-launchers/LightRAG-Web-Chat.ps1
```

### Telegram source registry and ad filtering

Добавлены web Telegram-источники:

```text
Obsidian-Test-Vault/20 Projects/Web Development/Sources/Telegram/Sitodel.md
Obsidian-Test-Vault/20 Projects/Web Development/Sources/Telegram/Private Web Group.md
```

`scripts/import-telegram-export.py` получил параметр:

```text
--ad-filter off|mark|separate|skip
```

Рекомендации:

```text
sitodel -> --ad-filter separate
private group -> --ad-filter mark
```

`separate` пишет подозрительные рекламные сообщения в:

```text
Filtered Ads
```

и ставит:

```yaml
lightrag_exclude: true
```

`vault_sources.py` теперь не индексирует Markdown с `lightrag_exclude: true` или `index: false`.

Интерактивный TTY-тест с вопросом:

```text
What is known about my-game? Give references.
```

Ответ вернулся с:

```text
References:
- 20 Projects/My Game/_README.md
```

Важно: не проверять кириллицу через PowerShell pipe. В pipe русские символы превращались в `?`. В интерактивном окне/TTY ввод работает нормально.

### Desktop chat launcher

Подготовлены launcher source files:

```text
desktop-launchers/LightRAG-Chat.cmd
desktop-launchers/LightRAG-Chat.ps1
```

Они должны открывать отдельное окно LightRAG Chat и предлагать выбор:

```text
1 - General knowledge
2 - My Game
```

Физически скопировать их в Desktop не удалось из-за ограничения среды/approval:

```text
C:\Users\Юрий\Desktop\LightRag\LightRAG-Chat.cmd
C:\Users\Юрий\Desktop\LightRag\LightRAG-Chat.ps1
```

Команды для следующего чата, если будет разрешение на Desktop write:

```powershell
Copy-Item -LiteralPath "desktop-launchers\LightRAG-Chat.cmd" -Destination "C:\Users\Юрий\Desktop\LightRag\LightRAG-Chat.cmd" -Force
Copy-Item -LiteralPath "desktop-launchers\LightRAG-Chat.ps1" -Destination "C:\Users\Юрий\Desktop\LightRag\LightRAG-Chat.ps1" -Force
```

После этого пользователь сможет нажать:

```text
C:\Users\Юрий\Desktop\LightRag\LightRAG-Chat.cmd
```

## Документация, обновленная в процессе

Создано/обновлено:

```text
SYSTEM_ARCHITECTURE.md
SYSTEM_HANDOFF.md
Automation-Requirements/YouTube-Transcription-Requirements.md
Obsidian-Test-Vault/30 Sources/YouTube/_README.md
Obsidian-Test-Vault/20 Projects/My Game/_README.md
```

`SYSTEM_ARCHITECTURE.md` описывает роли Obsidian, LightRAG, LM Studio, Codex.

`Automation-Requirements/YouTube-Transcription-Requirements.md` описывает сценарий "YouTube-ссылка в Obsidian -> transcript -> LightRAG".

## Что значит Sources

`Sources` - это первоисточники. Это не обязательно одна общая папка-свалка.

Желательный маршрут:

```text
10 Programming/Zenject/Sources/YouTube
20 Projects/My Game/Sources/YouTube
30 Sources/Telegram
30 Sources/Articles
```

Автоматическая сортировка идет по:

```text
scope
project
area
topic
tags
path
```

Если автоматике не хватает уверенности, следующий UX-вариант - desktop app, который спрашивает, куда положить материал.

## Что НЕ работает / не закончено

### Full general index

`LightRAG/rag_storage_general` пока не существует.

Причина: `general` сейчас содержит 33 Markdown-файла и около 729k символов, включая большие Telegram-файлы.

Самые большие general docs:

```text
302241 chars - 30 Sources/Telegram/Unity ресурсы/all All Messages.md
111946 chars - 10 Programming/Zenject/Sources/YouTube/DI + UNITY = ZENJECT ⚡️ Dependency injection в Unity [mbuzSrKHBHI].md
105825 chars - 30 Sources/Telegram/Unity ресурсы/0002 MultiPassFX - Fur and Cloud () #бесплатно.md
55759 chars - 30 Sources/Telegram/Unity ресурсы/0029 Статический анализ для игр () Вот понятно для чего, хочется использовать.md
```

Команда полного general reindex:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ingest-vault-scope-lmstudio.ps1 -Scope general
```

Но лучше сначала решить, нужен ли полный reindex сразу или инкрементальный/тематический.

### LM Studio Chat UI

Обычный LM Studio Chat UI не подключен к LightRAG.

Если пользователь пишет прямо в LM Studio Chat, модель не видит Obsidian, кроме вручную вставленного текста.

Нужный режим - отдельный launcher/app:

```text
LightRAG-Chat.cmd
```

Он вызывает `scripts/chat-vault-lmstudio.ps1`, а тот работает через LightRAG.

### Desktop launcher not copied

Launcher source files есть в проекте, но не скопированы на Desktop из-за ограничения записи в Desktop в текущей сессии.

Следующий чат должен первым делом скопировать:

```text
desktop-launchers/LightRAG-Chat.cmd -> C:\Users\Юрий\Desktop\LightRag\LightRAG-Chat.cmd
desktop-launchers/LightRAG-Chat.ps1 -> C:\Users\Юрий\Desktop\LightRag\LightRAG-Chat.ps1
```

### YouTube STT fallback

Сейчас работает captions/auto captions через `yt-dlp`.

Еще не добавлен fallback:

```text
faster-whisper
whisper.cpp
```

Нужен для видео без субтитров или с плохими auto captions.

### Obsidian watcher

Пока sync запускается вручную или при reindex.

Следующий уровень автоматизации:

- watcher за Obsidian vault;
- очередь обработки YouTube link notes;
- инкрементальный reindex;
- уведомление/desktop prompt, если система не уверена в topic/project.

## Быстрые команды

Запустить модели:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-knowledge-lab.ps1
```

Остановить модели:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop-knowledge-lab.ps1
```

Проверить YouTube links:

```powershell
.\LightRAG\.venv\Scripts\python.exe scripts\sync-youtube-links.py --scope general --list-only
```

Синхронизировать YouTube transcripts:

```powershell
.\LightRAG\.venv\Scripts\python.exe scripts\sync-youtube-links.py --scope general
```

Reindex project:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ingest-vault-scope-lmstudio.ps1 -Scope game -Project my-game
```

Ask project:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\query-vault-scope-lmstudio.ps1 -Scope game -Project my-game "Что известно по проекту my-game? Укажи references."
```

Chat project:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\chat-vault-lmstudio.ps1 -Scope game -Project my-game
```

Chat general после построения `rag_storage_general`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\chat-vault-lmstudio.ps1 -Scope general
```

## Рекомендуемый следующий план

1. Скопировать `LightRAG-Chat.cmd` и `LightRAG-Chat.ps1` в `C:\Users\Юрий\Desktop\LightRag`.
2. Проверить запуск чата по клику.
3. Решить, что делать с `general`: полный reindex или тематический/инкрементальный индекс.
4. Если Control должен быть только для проверки, убрать/перенести `05 Import Telegram Export`.
5. Добавить watcher для Obsidian YouTube link notes.
6. Добавить STT fallback для YouTube без captions.
7. Позже заменить PowerShell-window chat на полноценное desktop GUI.
