# LightRAG + Obsidian + LM Studio Handoff

Дата состояния: 2026-06-02.

Этот файл нужен как контекст для нового диалога с Codex. Если нужно продолжить настройку, доделать GUI или менять поведение системы, сначала покажи/прикрепи этот Markdown.

## Цель системы

Локальная система для работы с заметками и знаниями:

- Obsidian хранит заметки в Markdown.
- LightRAG читает Markdown, строит индекс/граф сущностей и связей.
- LM Studio предоставляет локальный OpenAI-compatible API.
- `qwen/qwen3-14b` отвечает на вопросы.
- `nomic-embed` делает embeddings для поиска.
- В будущем планируется удобный GUI в `C:\Users\Юрий\Desktop\LightRag`.

## Главные пути

Проект:

```text
C:\Users\Юрий\Documents\Freelance\AI-Knowledge-Lab
```

Obsidian vault:

```text
C:\Users\Юрий\Documents\Freelance\AI-Knowledge-Lab\Obsidian-Test-Vault
```

Папка запускателей и будущего GUI:

```text
C:\Users\Юрий\Desktop\LightRag
```

LM Studio CLI:

```text
C:\Users\Юрий\.lmstudio\bin\lms.exe
```

Python environment LightRAG:

```text
C:\Users\Юрий\Documents\Freelance\AI-Knowledge-Lab\LightRAG\.venv
```

## Проверенное состояние

Проверено:

- LM Studio server включается на `http://127.0.0.1:1234/v1`.
- Локальная LLM скачана и загружается: `qwen/qwen3-14b`, размер около `9.00 GB`.
- Embedding-модель скачана и загружается: `nomic-embed`, размер около `84 MB`.
- Obsidian подключен к правильному vault.
- LightRAG читает Markdown из Obsidian vault.
- LightRAG строит graph/index через Qwen3 и LM Studio.
- LightRAG query возвращает ответ с reference на исходную заметку.

Последний успешный полный тест:

```text
Chunk 1 of 2 extracted 6 Ent + 5 Rel
Chunk 2 of 2 extracted 1 Ent + 5 Rel
Writing graph with 12 nodes, 10 edges
Loaded graph ... with 12 nodes, 10 edges
Naive query: 2 chunks
References
- 10 Programming/Unity Workflow Notes.md
```

Это означает, что цепочка работает:

```text
Obsidian Markdown -> LightRAG -> graph/index -> LM Studio embeddings -> qwen/qwen3-14b -> answer
```

## Obsidian vault

Ожидаемая структура vault:

```text
Obsidian-Test-Vault
  .obsidian
  00 Inbox
    Capture Queue.md
  10 Programming
    Unity Workflow Notes.md
  20 Music
    Mixing and Mastering Notes.md
  30 Knowledge Work
    Large Information Workflow.md
  Home.md
```

Пользователь также создал тестовый файл:

```text
20 Music\ыфафы.md
```

Это подтвердило, что Obsidian пишет в тот же vault, который читает LightRAG.

Если в Obsidian видны файлы вроде `Без названия...`, а не папки `00 Inbox`, `10 Programming`, `20 Music`, значит открыт не тот vault или открыта Graph/Quick Switcher панель вместо File Explorer. Нужно открыть папку:

```text
C:\Users\Юрий\Documents\Freelance\AI-Knowledge-Lab\Obsidian-Test-Vault
```

## LM Studio

Текущие нужные модели:

```text
qwen/qwen3-14b
nomic-embed
```

Проверка статуса:

```powershell
C:\Users\Юрий\.lmstudio\bin\lms.exe status
C:\Users\Юрий\.lmstudio\bin\lms.exe ps
```

Ожидаемый статус:

```text
Server: ON (port: 1234)

Loaded Models
  · qwen/qwen3-14b - 9.00 GB
  · nomic-embed - 84.11 MB
```

Важная особенность Qwen3:

- Qwen3 может тратить ответ на `reasoning_content` и возвращать пустой `content`.
- Для рабочих запросов нужно добавлять `/no_think`.
- В скриптах для RAG это уже учтено.

Старая модель `qwen/qwen2.5-coder-32b` была установлена, но для LightRAG в LM Studio работала нестабильно: зависала или возвращала пустой content на entity-extraction prompt. Ее лучше не использовать для LightRAG.

## Desktop launchers

Папка:

```text
C:\Users\Юрий\Desktop\LightRag
```

Текущие файлы:

```text
01 Check LightRAG.cmd
02 Ask Obsidian Vault.cmd
03 Stop AI.cmd
04 Open Obsidian Vault.cmd

Check-LightRAG.ps1
Ask-Obsidian-Vault.ps1
Stop-AI.ps1
Open-Obsidian-Vault.ps1
README.txt
```

Почему так:

- `.cmd` файлы сделаны минимальными ASCII-обертками без кириллицы и без BOM.
- Они запускают `.ps1` файлы.
- Русские сообщения выводятся из PowerShell-файлов, где кодировка работает нормально.

Уже была проблема: `.cmd` с UTF-8 BOM и русским текстом ломались в `cmd.exe`, появлялось:

```text
яп╗┐@echo off
```

Поэтому не возвращать русскую логику прямо в `.cmd`. Для русского текста использовать `.ps1`.

## Назначение запускателей

```text
01 Check LightRAG.cmd
```

Запускает полный тест:

```text
Obsidian Markdown -> LightRAG -> LM Studio -> answer
```

Успешный признак:

```text
extracted ... Ent + ... Rel
Writing graph with ... nodes, ... edges
References: ...md
```

```text
02 Ask Obsidian Vault.cmd
```

Спрашивает вопрос в терминале и отправляет его в локальную RAG-систему.

```text
03 Stop AI.cmd
```

Выгружает модели и останавливает LM Studio server.

```text
04 Open Obsidian Vault.cmd
```

Открывает папку правильного Obsidian vault и показывает подсказку на русском.

## Основные скрипты проекта

Папка:

```text
C:\Users\Юрий\Documents\Freelance\AI-Knowledge-Lab\scripts
```

Важные файлы:

```text
run-lmstudio-test.cmd
run-lmstudio-test.ps1
ingest-vault-lmstudio.py
query-vault-lmstudio.py
simple-vault-rag-lmstudio.py
ask-vault-lmstudio.cmd
ask-vault-lmstudio.ps1
start-knowledge-lab.cmd
start-knowledge-lab.ps1
stop-knowledge-lab.cmd
stop-knowledge-lab.ps1
smoke-test.cmd
smoke-test.py
local_tokenizer.py
```

Назначение:

- `smoke-test.cmd` проверяет LightRAG без реальной LLM, с dummy embeddings/LLM.
- `run-lmstudio-test.cmd` проверяет LightRAG с LM Studio, Qwen3 и `nomic-embed`.
- `ingest-vault-lmstudio.py` читает Markdown из Obsidian vault и индексирует в LightRAG.
- `query-vault-lmstudio.py` задает вопрос LightRAG storage.
- `simple-vault-rag-lmstudio.py` быстрый vector-only RAG без полного графа LightRAG.
- `local_tokenizer.py` нужен, чтобы избежать сетевой загрузки tiktoken.

## Текущий режим использования

Минимальный пользовательский режим:

1. Открыть LM Studio.
2. Убедиться, что Server ON.
3. Убедиться, что загружены `qwen/qwen3-14b` и `nomic-embed`.
4. Открыть Obsidian vault:

```text
C:\Users\Юрий\Documents\Freelance\AI-Knowledge-Lab\Obsidian-Test-Vault
```

5. Для проверки запустить:

```text
C:\Users\Юрий\Desktop\LightRag\01 Check LightRAG.cmd
```

6. Для вопроса по vault запустить:

```text
C:\Users\Юрий\Desktop\LightRag\02 Ask Obsidian Vault.cmd
```

## Что НЕ происходит автоматически

Obsidian сам не запускает LightRAG.

Obsidian graph и LightRAG graph - разные вещи:

- Obsidian graph показывает ссылки между Markdown-заметками.
- LightRAG graph строится отдельно из текста заметок через LLM.

Сейчас индексация запускается вручную через скрипты. Позже можно добавить:

- watcher за изменениями Markdown;
- scheduled task;
- Obsidian plugin;
- локальный GUI, который будет дергать эти скрипты/модули.

## Идеи для будущего GUI

GUI лучше делать в:

```text
C:\Users\Юрий\Desktop\LightRag
```

Первый простой GUI может иметь кнопки:

- Проверить статус LM Studio.
- Загрузить модели.
- Проверить LightRAG.
- Задать вопрос vault.
- Открыть Obsidian vault.
- Остановить AI / выгрузить модели.

Полезные статусы для UI:

- LM Studio server: ON/OFF.
- LLM loaded: `qwen/qwen3-14b`.
- Embeddings loaded: `nomic-embed`.
- Vault path exists.
- Последняя индексация: storage folder, nodes/edges/chunks.
- Последний ответ и references.

GUI может сначала запускать существующие `.ps1` или Python-скрипты. Более чистый следующий шаг - сделать единый Python backend/CLI с командами:

```text
status
check
ask
ingest
stop
open-vault
```

После этого GUI будет вызывать один backend, а не много отдельных скриптов.

## Известные проблемы и решения

### CMD encoding

Проблема:

```text
яп╗┐@echo off
```

Причина: `.cmd` был сохранен в UTF-8 with BOM и с русским текстом.

Решение:

- `.cmd` только ASCII.
- Русский текст и логика в `.ps1`.

### Qwen3 empty content

Проблема: Qwen3 иногда пишет в `reasoning_content`, а `content` пустой.

Решение: добавлять `/no_think` в prompt. В LM Studio скриптах это уже добавлено.

### tiktoken network download

Проблема: LightRAG OpenAI embedding helper пытался скачать `cl100k_base.tiktoken`.

Решение: embedding-функция для LM Studio реализована напрямую через OpenAI-compatible endpoint, без tiktoken.

### Wrong Obsidian vault

Проблема: пользователь видел `Без названия...` вместо тестовых папок.

Причина: был открыт другой vault или Graph/Quick Switcher вместо File Explorer.

Решение: открыть как vault точную папку:

```text
C:\Users\Юрий\Documents\Freelance\AI-Knowledge-Lab\Obsidian-Test-Vault
```

## Что проверить после перезагрузки ПК

1. LM Studio открыт.
2. Server ON.
3. `qwen/qwen3-14b` loaded.
4. `nomic-embed` loaded.
5. Obsidian открыт на правильном vault.
6. Запустить:

```text
C:\Users\Юрий\Desktop\LightRag\01 Check LightRAG.cmd
```

Успешный результат:

```text
Writing graph with ... nodes, ... edges
References
```

## Рекомендация для следующего этапа

Следующий полезный этап - сделать в `C:\Users\Юрий\Desktop\LightRag` простой GUI, который:

- показывает статус системы;
- запускает проверку;
- принимает вопрос;
- показывает ответ и references;
- умеет остановить модели;
- не требует пользователю видеть терминал.

При разработке GUI не ломать уже работающие `.cmd`/`.ps1`; лучше добавить новые файлы рядом и постепенно заменить запускатели.
