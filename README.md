# v1rus-dev

Личный маркетплейс плагинов Claude Code: слоистые наборы правил, skills и агентов, чтобы стек-специфичные правила не грузились в каждую сессию.

## Установка

```
/plugin marketplace add ~/.claude/v1rus-dev
# или по git: /plugin marketplace add <git-url-placeholder>
/plugin install v1rus-android@v1rus-dev      # тянет compose -> kotlin -> core по dependencies
```

Для разработки: `claude --plugin-dir plugins/v1rus-core --plugin-dir plugins/v1rus-kotlin`.

## Плагины

| Плагин | Слой | Зависит от |
|---|---|---|
| v1rus-core | базовый charter, общие агенты/skills, движок правил | - |
| v1rus-kotlin | Kotlin / JVM / KMP | core |
| v1rus-compose | Jetpack Compose / Compose Multiplatform | kotlin |
| v1rus-android | платформа Android | compose |
| v1rus-go | Go | core |
| v1rus-typescript | TypeScript и JavaScript | core |

## Как доставляются правила

Плагины не могут нести CLAUDE.md или `.claude/rules` (см. `docs/PLUGIN-SPEC-NOTES.md`), поэтому каждый плагин содержит маленький движок (`hooks/v1rus_rules.py`): `charter.md` подмешивается на SessionStart, `rules/*.md` с `paths:` - при Write/Edit подходящего файла, один раз за сессию.

Контракт для авторов: `docs/CONVENTIONS.md`. Правила репозитория: `CLAUDE.md`.
