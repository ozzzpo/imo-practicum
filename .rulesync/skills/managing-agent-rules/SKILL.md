---
name: managing-agent-rules
description: Как устроены правила и навыки агентов в этом репозитории — источник в .rulesync/, генерация CLAUDE.md, AGENTS.md и деревьев навыков через rulesync, добавление навыка, проверка актуальности в CI. Use when меняешь правило или навык агента, трогаешь CLAUDE.md, AGENTS.md, .claude/skills, .agents/skills, .opencode/skills или rulesync.jsonc.
targets: ["*"]
---

# Правила и навыки агентов

Правила пишутся один раз в `.rulesync/`, а [rulesync](https://github.com/dyoshikawa/rulesync) генерирует файлы для Claude Code, Codex CLI и OpenCode. Настройки — в `rulesync.jsonc`.

| Источник | Что из него получается |
|---|---|
| `.rulesync/rules/00-practicum.md` | `CLAUDE.md` и `AGENTS.md` с одинаковым текстом |
| `.rulesync/skills/<slug>/SKILL.md` | `.claude/skills/`, `.agents/skills/`, `.opencode/skills/` |
| `.rulesync.local/` | Личные дополнения участника, игнорируется Git |

**Сгенерированные файлы руками не правятся.** Меняй источник, перегенерируй и коммить источник вместе с результатом. CI (`.github/workflows/agent-rules.yml`) падает, если они разошлись.

## Команды

Нужен Node.js. Версия rulesync закреплена, чтобы у всех получался одинаковый результат.

```bash
npx --yes rulesync@16.24.0 generate           # перегенерировать
npx --yes rulesync@16.24.0 generate --check   # проверить без записи, то же делает CI
```

Версия указана в `.github/workflows/agent-rules.yml`, `docs/workflow.md`, в шапке и в разделе команд `00-practicum.md` и в этом навыке. Меняй её везде сразу.

## Добавление навыка

1. Slug — kebab-case, начинается с действия: `preparing-defense`.
2. Создай `.rulesync/skills/<slug>/SKILL.md`:

   ```yaml
   ---
   name: preparing-defense   # совпадает с именем папки
   description: Что покрывает + «Use when …». Это единственный текст, который агент видит до открытия навыка.
   targets: ["*"]
   ---
   ```

3. Пиши по-русски, как остальные навыки: конкретные команды и пути, разделы «Чеклист» и «Не делай». Пути пиши от корня репозитория без относительных ссылок: навык копируется в несколько папок.
4. Добавь строку в таблицу «Навыки» в `.rulesync/rules/00-practicum.md`.
5. Перегенерируй и проверь.

## Что куда

- Правило для любой задачи и короткое — в `00-practicum.md`. Его агент читает всегда, поэтому держи файл кратким.
- Подробная инструкция для одного вида задач — в навык.
- Договорённости для людей — в `docs/workflow.md` и `docs/decisions.md`. Правило ссылается на них, а не копирует.

## Не делай

- Не правь `CLAUDE.md`, `AGENTS.md` и деревья навыков руками — следующий `generate` перезапишет правку, а CI упадёт.
- Не клади навык прямо в `.claude/skills/`: `delete: true` удалит его при генерации.
- Не меняй версию rulesync только в одном месте.
