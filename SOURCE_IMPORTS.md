# Source Imports

## Контексты

Vault остается одним, но заметки разделяются по контекстам:

- `scope: general` - общая база знаний, например Unity-ресурсы, статьи, курсы, Telegram-ссылки.
- `scope: game` + `project: my-game` - информация именно по твоей игре.

LightRAG-скрипты читают эти поля из frontmatter. Если frontmatter нет, папки `10 Programming`, `10 General Knowledge` и `30 Sources` считаются `general`, а `20 Projects/<project>` считается `game`.

## Telegram

### Export mode

1. В Telegram Desktop открой канал или группу.
2. Меню -> Export chat history.
3. Выбери Machine-readable JSON.
4. Запусти `05 Import Telegram Export.cmd` из `C:\Users\Юрий\Desktop\LightRag`.
5. Укажи путь к `result.json`.

Импорт создаст Markdown-файлы в:

```text
Obsidian-Test-Vault\30 Sources\Telegram\<название канала>\
```

### Sync mode

Для живой синхронизации по ссылке используется отдельная иконка:

```text
C:\Users\Юрий\Desktop\Sync Telegram Unity.cmd
```

Первый запуск требует Telegram API credentials:

1. открой `https://my.telegram.org/apps`;
2. создай приложение;
3. скопируй `api_id` и `api_hash`;
4. введи их в окне синхронизации вместе с телефоном Telegram.

После первого входа локальная session сохраняется в:

```text
C:\MyFiles\KnowledgeLab\.telegram-sync
```

Синхронизация:

- открывает `https://t.me/+Ct9ip7LnMzNlN2M6`;
- получает темы Telegram-группы;
- пишет каждую тему отдельным Markdown-файлом;
- хранит `tg-msg:<id>` блоки и `last_id`, поэтому повторный запуск не дублирует сообщения.

## Scoped questions

- `06 Ask General Knowledge.cmd` спрашивает только по общей базе.
- `07 Ask My Game.cmd` спрашивает только по `scope: game`, `project: my-game`.
- `08 Reindex LightRAG Scope.cmd` строит отдельный LightRAG storage для выбранного scope.
