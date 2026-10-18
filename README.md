# v1rus-dev

Маркетплейс плагинов для [Claude Code](https://code.claude.com/docs) — инженерные
стандарты v1rus, оформленные так, чтобы агент их выполнял, а не читал.

Плагины ставятся один раз и работают в любом проекте: правила общения и качества, обязательные гейты,
конвенции по стекам, ревью-агенты и многоагентный feature-pipeline.

---

## Зачем это нужно

Раньше знание жило в двух местах: в `CLAUDE.md` конкретного проекта и в личном `~/.claude` конкретного
разработчика. Отсюда три проблемы:

- **Не шарится.** У кого-то настроены агенты и правила, у кого-то нет — качество результата зависит от
  того, чей ноутбук.
- **Дублируется.** Одни и те же конвенции переписываются в каждом новом проекте, расходятся и устаревают.
- **Не проверяется.** «Все строки из ресурсов», «фичи не зависят друг от друга», «не коммить в main» —
  правила, которые держались на внимательности ревьюера.

Плагины решают всё три: единый источник, установка одной командой, а часть правил стала
**механически проверяемой** — хуками и линтерами, а не напоминаниями.

---

## Слои

Плагины сложены в граф зависимостей. Ставишь листовой — базовые приезжают автоматически.

```
v1rus-core                        процесс, коммуникация, гейты, ревью-агенты, pipeline
  │
  ├── v1rus-kotlin                Kotlin + JVM + Gradle
  │     └── v1rus-compose         Compose: UI, MVI, Koin, производительность
  │           ├── v1rus-kmp       KMP + iOS: commonMain, expect/actual, Swift
  │           └── v1rus-android   нативный Android: модули, манифест, Room + Ktor
  │
  ├── v1rus-flutter               Flutter + Dart
  │
  ├── v1rus-go                    Go: правила, проверка, агенты
  │
  ├── v1rus-typescript            TypeScript: типы, границы I/O, ESM, ESLint
  │     ├── v1rus-node            бэкенд: NestJS, Prisma, конфиг, очереди
  │     └── v1rus-react           веб: React + Next App Router, состояния, a11y
  │
  └── v1rus-dotnet                C# + ASP.NET Core: слои, EF Core, ProblemDetails

v1rus-fullstack                   шов между v1rus-node и v1rus-react: монорепа,
                                   контракт API, сессия, e2e — зависит от обоих
```

Принцип: **правило живёт на самом верхнем слое, где оно ещё верно.** «Не коммить в main» — в `core`.
`implementation` вместо `api` — в `v1rus-kotlin`. Всё про Compose — UI, MVI, рекомпозиции — в
`v1rus-compose`, потому что одинаково верно для CMP и Jetpack Compose. `commonMain` без `java.*` — в
`v1rus-kmp`, потому что верно только там. Строгий `tsconfig` и валидация на границе ввода — в
`v1rus-typescript`, потому что одинаково верно и для бэкенда, и для веба. Контракт API — в
`v1rus-fullstack`, потому что он неверен ни для одной половины по отдельности. Правило не копируется
в два слоя: копии расходятся.

---

## Быстрый старт

### 1. Подключить marketplace

```bash
claude plugin marketplace add v1rus-dev/v1rus-claude-plugins
# или явным URL: claude plugin marketplace add git@github.com:v1rus-dev/v1rus-claude-plugins.git
```

Для локальной разработки самих плагинов можно подключить клон:

```bash
claude plugin marketplace add ./путь/к/v1rus-claude-plugins
```

Локальный путь обязательно начинается с `./` или `/` — голое `.` не принимается.

> В репозиторий не попадает ничего, кроме конвенций: ни секретов, ни токенов, ни внутренних адресов,
> ни данных клиентов. `.gitignore` закрывает очевидное, но полагаться стоит на дисциплину.

### 2. Поставить плагин под свой стек

```bash
claude plugin install v1rus-kmp@v1rus-dev        # приедут v1rus-compose, v1rus-kotlin, v1rus-core
claude plugin install v1rus-android@v1rus-dev    # то же самое, без iOS-части
claude plugin install v1rus-flutter@v1rus-dev    # приедет v1rus-core
claude plugin install v1rus-dotnet@v1rus-dev     # приедет v1rus-core
claude plugin install v1rus-go@v1rus-dev         # приедет v1rus-core
claude plugin install v1rus-node@v1rus-dev       # приедут v1rus-typescript, v1rus-core
claude plugin install v1rus-react@v1rus-dev      # то же самое, веб-половина
claude plugin install v1rus-fullstack@v1rus-dev  # приедут обе половины и всё под ними
```

| Чем занимаешься | Что ставить |
|---|---|
| KMP / Compose Multiplatform | `v1rus-kmp` |
| Нативный Android | `v1rus-android` |
| Flutter | `v1rus-flutter` |
| Kotlin-бэкенд, Gradle-инфраструктура, библиотека | `v1rus-kotlin` |
| Бэкенд на C# / ASP.NET Core | `v1rus-dotnet` |
| Go-сервис, CLI или библиотека | `v1rus-go` |
| Бэкенд на Node.js / NestJS | `v1rus-node` |
| Веб-фронтенд на React / Next | `v1rus-react` |
| Монорепа, где бэкенд и веб живут вместе | `v1rus-fullstack` |
| TypeScript-библиотека или CLI без фреймворка | `v1rus-typescript` |
| Не мобильная разработка, нужны только процесс и ревью | `v1rus-core` |

### 3. Выбрать scope

```bash
claude plugin install v1rus-kmp@v1rus-dev --scope user      # для всех своих проектов (по умолчанию)
claude plugin install v1rus-kmp@v1rus-dev --scope project   # для этого репозитория, попадает в git
claude plugin install v1rus-kmp@v1rus-dev --scope local      # только для себя в этом репозитории
```

- **`user`** — обычный выбор разработчика.
- **`project`** — когда команда должна получить одинаковый набор: запись уходит в
  `.claude/settings.json` репозитория, и у всех подтягивается автоматически.
- **`local`** — попробовать, ничего не ломая: пишется в `.claude/settings.local.json`.

Всё то же самое доступно интерактивно — команда `/plugin` внутри сессии.

---

## Что внутри

Подробности — в README самих плагинов.

### [`v1rus-core`](plugins/v1rus-core/) — база, стек-агностичная

| | |
|---|---|
| **Инженерный чартер** | Инжектится в каждую сессию: язык и тон общения, non-negotiables (никакого `sudo`, никакого обхода git-хуков, никаких коммитов в `main`, PR только по запросу), принципы (минимальный диff, не соглашаться по умолчанию, эмпирическая проверка вместо теории), четыре обязательных гейта |
| **Хуки-предохранители** | `git-guard` блокирует `sudo`, `--no-verify`, plain `--force`, коммит и push из `main`/`master`/`develop`. `secrets-guard` — доступ к секретам и команды-эксфильтраторы |
| **Правила как скиллы** | `v1rus-workflow` (гейты + маршрутизация по типам задач), `v1rus-qa` (шкала сложности 1–10 и когда вообще пишутся тесты), `v1rus-code-policies`, `v1rus-sources` (T1–T4 доверия к источникам), `v1rus-logging`, `v1rus-dependencies`, `v1rus-code-search` |
| **Процессные скиллы** | `check` (build + анализ + тесты), `finalize` (review→fix→simplify до PASS), `interview` (расспросить разработчика и изучить вопрос до старта), `write-spec`, `write-plan`, `write-tests`, `generate-test-plan`, `multiexpert-review`, `research`, `evaluate-dependency` |
| **Ревью-агенты** | `code-reviewer`, `architecture-expert`, `security-expert`, `ux-expert`, `business-analyst`, `designer`, `source-researcher`, `dependency-evaluator` |
| **Feature-pipeline** | `/feature` и `/bugfix` — многоагентный конвейер: требования → архитектура → гейт подтверждения со скорингом сложности → тест-план → разработка → тест-луп → finalize → code review → экспертные ревью → отчёт, три коммита-майлстоуна и resume через `STATE.md`. Агенты конвейера стек-агностичны: словарь стека приходит из профиля, который везёт слой технологии (`*-pipeline-profile`), — один каркас на все стеки вместо копии конвейера под каждый |
| **Режимы конвейера** | Две независимые оси. Скорость: `standard` (по умолчанию, полная последовательность) и `lite` — `/feature --lite` или `/feature-lite`: требования без gap-check агента (планка вопросов та же — lite режет гейты и агентов, но не уточнение задачи), план на одну страницу, авто-approve гейта подтверждения, без `feature-finalizer`, один раунд ревью, один коммит вместо трёх. Lite не трогает пол проверки: сборка выполняется всегда, бэнды сложности из `v1rus-qa` действуют, `security-expert` обязателен на security-поверхности, а план со сложностью >=7 останавливает lite-прогон и требует решения пользователя. Вопросы: `normal` (по умолчанию — спрашивает то, что блокирует критерии приёмки) и `quiet` — `--quiet`: аналитик отрабатывает как обычно, но его открытые вопросы закрывает сам оркестратор и пишет их в `ASSUMPTION`-леджер, гейт подтверждения авто-аппрувится. `quiet` не глушит жёсткие блокеры — противоречие в задаче, политику на security/деньгах/миграции, отсутствие доступов, risk-триггеры. Оси комбинируются: `--lite --quiet` — «маленькая задача, не дёргай меня» |
| **`/review`** | Независимое ревью пути, модуля или рабочего диффа с автоматической эскалацией к экспертам |
| **`/mvp-init`** | Создание нового приложения с нуля из описания продукта: бриф → выбор стека → план каркаса с графом модулей и зависимостями → обязательный гейт → бутстрап → `CLAUDE.md` целевого проекта → сборка → бэклог MVP командами `/feature`. Команда стек-агностична; как именно инициализировать конкретную технологию, знает её слой — скилл `*-mvp-blueprint` (контракт: [`references/mvp-blueprint.md`](plugins/v1rus-core/references/mvp-blueprint.md)) |

### [`v1rus-kotlin`](plugins/v1rus-kotlin/) — Kotlin, JVM, Gradle

Правила видимости и коллекций, коroutine/Flow-ловушки, `implementation` против `api`, version catalogs,
`ksrc` и dependency-intelligence. Агенты `kotlin-engineer`, `build-engineer`, `performance-expert`.

### [`v1rus-compose`](plugins/v1rus-compose/) — Compose на любом таргете

Всё, что одинаково верно для Compose Multiplatform и Jetpack Compose: разделение Destination ⇄ Screen,
MVI-презентация, чеклист состояний экрана и доступности, один composable на файл с превью, анимации,
типизированные роуты с диалогами и bottom sheets как destination'ами, Koin, локализация — плюс 26
скиллов по производительности и стабильности (stability inference, strong skipping, трассировка
рекомпозиций, lazy-layouts, отложенные чтения state, `Modifier.Node`, R8, baseline profiles,
release-режим, hot reload, CI-гейты). Агент `compose-developer`, правило `compose-files.md`.

Отдельно ставить обычно не нужно — приезжает с `v1rus-kmp` или `v1rus-android`.

### [`v1rus-kmp`](plugins/v1rus-kmp/) — KMP и iOS

Только собственно многоплатформенное: `commonMain` и `expect/actual`, граф модулей и source sets,
data-layer с Room-билдером и Ktor-клиентом через `expect/actual`, `commonTest`, профиль
`kmp-pipeline-profile`. Агенты `swift-engineer`, `swiftui-developer`, `test-runner`. Compose-часть
приходит из `v1rus-compose`.

### [`v1rus-android`](plugins/v1rus-android/) — нативный Android

Граф Gradle-модулей Android-приложения без source sets, манифест и разрешения, дисциплина `Context` и
жизненного цикла, data-layer на Room + Ktor поверх OkHttp + DataStore, разделение `src/test` и
`src/androidTest`, профиль `android-pipeline-profile`. Агент `test-runner`. Своего движка слой не
везёт намеренно: UI пишет `v1rus-compose:compose-developer`, логику — `v1rus-kotlin:kotlin-engineer`.

### [`v1rus-flutter`](plugins/v1rus-flutter/) — Flutter и Dart

Слои `core / design_system / domain / data / features` с границами, которые держит analyzer-плагин;
Bloc на экраны и Cubit на компоненты; эффекты отдельным потоком; sealed `Result` на границе data; Retrofit
поверх Dio с single-flight refresh; Drift + secure storage + preferences; get_it модулями по фичам;
типизированные роуты go_router; модели без кодогенерации — нативные `sealed`-классы + `equatable`;
ARB + `gen-l10n` с проверкой синхронности локалей в CI; профиль `flutter-pipeline-profile`, которым
feature-pipeline получает Flutter-словарь. Агенты `flutter-engineer`, `flutter-ui-developer`,
`test-runner`.

### [`v1rus-dotnet`](plugins/v1rus-dotnet/) — C# и ASP.NET Core

Бэкенд на .NET: четыре проекта `Api / Application / Domain / Infrastructure`, направление зависимостей
держат project references и architecture-тесты; minimal API endpoint-модулями вместо контроллеров;
`Result<T>` с закрытой иерархией `DomainError` на ожидаемые отказы и один `IExceptionHandler` →
`ProblemDetails` на всё остальное; use case без медиатора; EF Core в Infrastructure за репозиториями,
миграции — шаг деплоя, не startup; типизированные клиенты через `IHttpClientFactory`; options pattern и
запрет секретов в `appsettings.json`; `ILogger<T>` message templates; xUnit + `WebApplicationFactory` +
Testcontainers с явным запретом EF in-memory. Правила инжектятся по типу файла: `csharp.md` на любой
`.cs`, `aspnetcore.md` на `Program.cs` и эндпоинты, `efcore.md` на `DbContext`, миграции и репозитории.
Профиль `dotnet-pipeline-profile`, блюпринт `dotnet-mvp-blueprint`. Агенты `dotnet-engineer`,
`test-runner`.

### [`v1rus-go`](plugins/v1rus-go/) — Go

Path-scoped правила для `.go`, `go.mod`, тестов, SQL и build-конфигов, поток проверки (`go-verify`),
скиллы под HTTP-эндпоинты, БД, ошибки и логирование, конкурентность, зависимости и релизную сборку.
Агенты `go-engineer`, `go-reviewer`, `go-test-runner`.

### [`v1rus-typescript`](plugins/v1rus-typescript/) — TypeScript как язык

Слой без фреймворка, общий для бэкенда и веба: строгий `tsconfig` и что именно даёт каждый флаг сверх
`strict`, ESM и `moduleResolution`, `tsc --noEmit` как гейт (зелёная сборка бандлером не доказывает
ничего); моделирование типов — discriminated unions вместо мешка опциональных полей, `never`-guard в
конце `switch`, `satisfies` вместо `as`, branded id; валидация на каждой границе ввода с выводом типа из
схемы — и отдельный раздел «где валидировать не надо»; `Error` с `cause` и таблица «Result или throw»;
плавающие промисы, ограниченная конкурентность, `AbortSignal` как прокидываемый параметр; `exports`-мапа
и запрет глубоких импортов; flat-config ESLint с type-aware правилами. Агентов и профиля стека нет
намеренно: «TypeScript» — не стек, в нём нельзя разложить проект.

Отдельно ставить имеет смысл только под библиотеку или CLI; иначе приезжает с `v1rus-node` или
`v1rus-react`.

### [`v1rus-node`](plugins/v1rus-node/) — бэкенд на Node.js и NestJS

Фиче-модули, внутри которых слои — папки, а не четыре Nest-модуля: единственная граница, которую Nest
реально держит, — это `exports`; DI и ловушка request-scope, всплывающего вверх по цепочке инъекции;
DTO с `whitelist` и ответы об ошибке в формате RFC 9457; Prisma за границей репозитория, чтобы ORM-модель
не утекала в домен, N+1 и транзакции, не держащие сетевой вызов; окружение парсится один раз на старте и
инжектится типизированным конфигом; блокировки event loop, backpressure и graceful shutdown; pino с
correlation id через `AsyncLocalStorage`; BullMQ с transactional outbox; Vitest + supertest поверх
Testcontainers, без замоканной Prisma. Профиль `node-pipeline-profile`, блюпринт `node-mvp-blueprint`.
Агенты `node-engineer`, `test-runner`.

### [`v1rus-react`](plugins/v1rus-react/) — веб-фронтенд на React и Next

Server components по умолчанию, `"use client"` прижат к листьям; фиче-папки рядом с деревом роутов;
серверное состояние живёт в server component или в TanStack Query и никогда не копируется в `useState`;
URL — место по умолчанию для того, что должно переживать перезагрузку и шариться ссылкой; чеклист
состояний и доступности того же калибра, что в `v1rus-compose` (loading / empty / error с повтором /
not-found / content, выход доступен в любом состоянии, фокус после навигации, настоящие элементы вместо
`div onClick`, клавиатура, контраст); токены темы вместо сырых значений; react-hook-form + zod-резолвер
с обязательной перепроверкой на сервере; next-intl с проверкой расхождения локалей в CI; Vitest +
Testing Library + MSW на транспортной границе, Playwright на сценарии. Профиль `web-pipeline-profile`,
блюпринт `web-mvp-blueprint`. Агенты `web-developer`, `test-runner`.

### [`v1rus-fullstack`](plugins/v1rus-fullstack/) — шов между бэкендом и вебом

Маленький слой намеренно: в нём только то, что неверно ни для одной половины по отдельности. pnpm
workspaces и граф задач Turborepo, кто кому имеет право быть зависимостью; контракт API объявлен один раз
в общем schema-пакете с route-дескрипторами — переименованный путь становится ошибкой typecheck, а не
404, а альтернативы (OpenAPI с генерацией клиента, end-to-end typed RPC) описаны с условиями, когда они
выигрывают; сессия через HttpOnly-куку, single-flight refresh с reuse-detection и правило двух URL для
API (браузер против серверного процесса фронтенда); разделение env с жёсткой линией «серверный секрет не
попадает в клиентский бандл»; contract-тесты и e2e через шов. Профиль `fullstack-pipeline-profile`
работает композицией — загружает профили обеих половин и переставляет план на contract-first. Своих
агентов-инженеров нет: эскалация в `v1rus-node:node-engineer` и `v1rus-react:web-developer`.

---

## Как это работает

Полезно понимать механику — она объясняет, почему одни правила приходят сами, а другие надо позвать.

### Чартер вместо общего `CLAUDE.md`

Плагины Claude Code **не умеют раздавать `CLAUDE.md`** — в официальной документации это сказано прямо:
`CLAUDE.md` в корне плагина не подключается как контекст проекта, и каталога `rules/` у плагина нет.
Контекст плагин отдаёт только через скиллы, агентов и хуки.

Поэтому корпоративная база — это `SessionStart`-хук, возвращающий `additionalContext`:
[`plugins/v1rus-core/hooks/charter.md`](plugins/v1rus-core/hooks/charter.md). Хочешь изменить базовое
поведение для всей компании — правишь один этот файл.

### Path-scoped правила

`~/.claude/rules/*.md` с фронтматтером `paths:` умеют подгружаться по типу файла. У плагинов такого
механизма нет, поэтому он воспроизведён хуком `path-rules.py`: перед `Edit`/`Write` он находит правила,
чьи `paths:`-глобы совпали с файлом, и инжектит их тело.

```
lib/features/orders/bloc/order_bloc.dart  →  rules/dart.md + rules/bloc.md
shared/domain/.../UseCase.kt              →  rules/kotlin-style.md + rules/coroutines.md + rules/commonmain.md
build.gradle.kts                          →  rules/gradle-style.md
```

Тело правила инжектится **один раз за сессию** (и ещё раз после компактификации контекста — `PreCompact`
сбрасывает отметку). Каждый слой везёт свою копию `path-rules.py`: `${CLAUDE_PLUGIN_ROOT}` резолвится
по-плагинно, и слой не может прочитать `rules/` соседа — это то, что делает слои независимо
устанавливаемыми.

### Скиллы подгружаются по описанию

Глубокие правила лежат скиллами и грузятся, когда релевантны. Поэтому `description` у скилла — не
документация, а **условие срабатывания**: там перечислены и темы, и триггерные формулировки. Скилл с
размытым описанием не вызовется никогда.

Позвать вручную: `/v1rus-core:v1rus-qa`, `/v1rus-flutter:flutter-architecture`.

### Namespacing и приоритеты

Компоненты плагина неймспейснуты именем плагина: `/v1rus-core:feature`,
агент `v1rus-kmp:test-runner`. Поэтому:

- **Проектная копия выигрывает.** Если в репозитории есть свой `.claude/commands/feature.md`, `/feature`
  останется проектным — плагинный доступен как `/v1rus-core:feature`. Конфликта нет, миграцию можно
  делать постепенно.
- **`CLAUDE.md` проекта важнее чартера.** Расхождение проговаривается один раз и решается в пользу
  проекта.
- **Плагин везёт паттерн, проект везёт имена.** Конкретные пути модулей, реальные имена `AppNavigator`,
  `StoreViewModel`, `AppTheme`, названия gradle-таск — читаются из `CLAUDE.md` проекта. Ни один агент не
  придумывает путь и не угадывает команду сборки.

### Что стало проверяемым, а не устным

| Правило | Чем держится |
|---|---|
| Не коммить в `main`, не обходить хуки, не `sudo` | `git-guard` — `PreToolUse` на Bash, блокирует до выполнения |
| Не читать секреты, не эксфильтрировать | `secrets-guard` |
| Конвенции языка приходят до написания кода (Kotlin, Dart, C#, TypeScript, React) | `path-rules` инжектит правило перед правкой файла |
| Фичи не зависят друг от друга (Flutter) | `import_lint` — нарушение падает как error в `dart analyze` и ломает CI |
| Каждый ключ переведён во всех локалях (Flutter) | `untranslated-messages-file` в `l10n.yaml` — CI падает, если файл не пуст |
| Каждый ключ переведён во всех локалях (Web) | проверка расхождения ключей и ICU-аргументов в CI |
| Слои .NET не зависят друг от друга не в ту сторону | project references + architecture-тесты в `tests/<Product>.ArchitectureTests` |
| Бэкенд и веб не расходятся по контракту API | общий schema-пакет + `typecheck` по всей монорепе + contract-тесты |

---

## Стоимость контекста

Измерено `claude plugin details` (в always-on не входит чартер — хук инжектится в рантайме,
это ещё ~2.2k токенов):

| Плагин | Always-on | Компоненты |
|---|---|---|
| `v1rus-core` | ~8.6k | 21 скилл, 16 агентов |
| `v1rus-kotlin` | ~3.0k | 4 скилла, 3 агента |
| `v1rus-compose` | ~11.5k | 35 скиллов, 1 агент |
| `v1rus-kmp` | ~3.5k | 4 скилла, 3 агента |
| `v1rus-android` | ~1.5k | 4 скилла, 1 агент |
| `v1rus-flutter` | ~4.8k | 15 скиллов, 3 агента |
| `v1rus-dotnet` | ~4.6k* | 13 скиллов, 2 агента |
| `v1rus-go` | не измерено | 12 скиллов, 3 агента |
| `v1rus-typescript` | ~2.9k* | 8 скиллов, без агентов |
| `v1rus-node` | ~4.9k* | 13 скиллов, 2 агента |
| `v1rus-react` | ~4.5k* | 13 скиллов, 2 агента |
| `v1rus-fullstack` | ~2.7k* | 7 скиллов, без агентов |

\* Пять новых слоёв ещё не измерены `claude plugin details` — цифры со звёздочкой оценены по объёму
описаний скиллов и агентов с калибровкой на измеренных слоях. Точное число появится после установки.

Реальные сочетания с чартером: Flutter-разработчик ≈ **15k**, Android-разработчик ≈ **27k**,
KMP-разработчик ≈ **29k**, Node-бэкендер ≈ **18k**, веб-разработчик ≈ **18k**, fullstack ≈ **26k**,
.NET-бэкендер ≈ **15k**. Основная часть мобильных сочетаний — общий Compose-слой; выделение его из `v1rus-kmp` цену для
KMP не изменило (те же скиллы, другой плагин), но Android-слой получил их бесплатно вместо копии.
Основное — описания скиллов и агентов, тела грузятся только при вызове. Свою цифру всегда можно
посмотреть:

```bash
claude plugin details v1rus-kmp@v1rus-dev
```

Если для конкретного проекта слой лишний — его можно отключить, не удаляя:

```bash
claude plugin disable v1rus-kmp --scope project
```

---

## Требования и ограничения

- **`python3` в `PATH`** — на нём работают хуки. Если его нет, хуки не запускаются (fail-open: сессия не
  ломается, но чартер и предохранители не активны). На Windows либо WSL, либо шим `python3`; установщик
  python.org сам его не создаёт.
- **Dart 3.10+ / Flutter 3.38+** — для `import_lint` в Flutter-проектах, поскольку раньше не было
  механизма analyzer-плагинов. На более старом SDK правила границ остаются в `CLAUDE.md` проекта и
  проверяются на ревью — и это проговаривается явно, а не замалчивается.
- **Никаких версий пакетов в плагинах.** Внутри только имена; версия резолвится на этапе плана через
  гейт `v1rus-dependencies` (`maven-mcp` для JVM, `dart pub outdated` и pub.dev для Dart). Пин в
  документации гниёт быстрее, чем его успевают обновить.

---

## Обновление и удаление

```bash
claude plugin marketplace update v1rus-dev     # подтянуть новые версии из репозитория
claude plugin update v1rus-kmp             # обновить плагин (нужен рестарт сессии)
claude plugin list                          # что установлено, в каком scope, включено ли
claude plugin details v1rus-core@v1rus-dev    # инвентарь компонентов и стоимость
claude plugin disable v1rus-kmp            # выключить, не удаляя
claude plugin uninstall v1rus-kmp --prune  # удалить вместе с осиротевшими зависимостями
claude plugin prune                         # подчистить auto-installed зависимости
claude plugin marketplace remove v1rus-dev     # отключить marketplace целиком
```

`--prune` удаляет только то, что приехало как зависимость и больше никому не нужно; установленное руками
не трогается.

---

## Доработка

### Куда что кладётся

```
CLAUDE.md                      правила работы с этим репозиторием (для агента)
scripts/check-plugins.py       проверка версий и структуры
.githooks/pre-commit           локальный гейт

plugins/<плагин>/
  .claude-plugin/plugin.json   манифест: имя, версия, описание, dependencies
  hooks/hooks.json             регистрация хуков
  hooks/*.py                   сами хуки
  rules/*.md                   path-scoped правила (фронтматтер paths:)
  skills/<имя>/SKILL.md        скилл; references/ рядом для глубокого материала
  agents/<имя>.md              субагент
  commands/<имя>.md            команда (плоский .md)
  README.md
```

Каталоги — дефолтные, поэтому пути компонентов в `plugin.json` **не указываются**: явное
`"agents": "./agents"` валидатор отвергает.

### Решить, на каком слое место правилу

Один вопрос: **на каком самом верхнем слое это правило всё ещё верно?** Там ему и жить. Правило,
верное для Kotlin и Dart одновременно, — в `core`. Верное для любого Kotlin-проекта, включая бэкенд, —
в `v1rus-kotlin`. Верное для Compose на любом таргете — в `v1rus-compose`. Только для CMP/iOS — в
`v1rus-kmp`, только для нативного Android — в `v1rus-android`.

### Правило или скилл

| Кладите правилом (`rules/`) | Кладите скиллом (`skills/`) |
|---|---|
| Бесполезно, если придёт после правки файла | Можно и нужно позвать по теме |
| Привязано к типу файла | Привязано к задаче |
| Компактно (инжектится целиком) | Может быть большим |

Дублировать текст между `rules/` и `skills/` нельзя. Тело живёт в `rules/`, а скилл — тонкая «входная
дверь» со ссылкой `${CLAUDE_PLUGIN_ROOT}/rules/<файл>.md` для ревью и планирования, где правки нет и
инжекта не будет.

### Про `description`

Это условие вызова. Перечисляйте темы и формулировки, по которым скилл должен сработать, и явно пишите,
когда он **не** нужен. Правило хорошего описания: прочитав только его, можно понять, стоит ли грузить
скилл, не открывая тело.

### Агенты

Фронтматтер агента — YAML. Многострочное `description` пишите **блочным скаляром**:

```yaml
description: |-
  Первая строка…

  <example>…</example>
```

Кавычки со строками, начинающимися с нулевой колонки, YAML не разбирает — агент тогда загружается с
пустыми метаданными и **не появляется в списке доступных вообще**. Это молчаливая поломка: `tools`,
`model`, `disallowedTools` просто отбрасываются. Именно так были сломаны четыре агента, перенесённых в
эти плагины.

### Версии — обязательный bump

`version` в `plugin.json` **пинит плагин**: изменил содержимое, не поднял версию — у команды не приедет
ничего, молча и без ошибки. Это единственная ошибка в этом репозитории, которую не видно на ревью, поэтому
её ловит тулинг.

**Любое изменение внутри `plugins/<имя>/` сопровождается bump'ом `version` в том же коммите.**

| Разряд | Когда |
|---|---|
| **patch** | правка без изменения поведения агента: опечатка, переформулировка, уточнение примера |
| **minor** | новый скилл / агент / команда / path-правило, новый раздел в существующем скилле |
| **major** | удаление или переименование скилла/агента/команды, смена `dependencies`, разворот правила |

Переименование скилла — major даже без правки тела: на него ссылаются другие скиллы и агенты.

### Проверка перед PR

```bash
git config core.hooksPath .githooks                  # один раз на клон — включает pre-commit
python3 scripts/check-plugins.py --staged            # версии + структура (то же, что хук)
python3 scripts/check-plugins.py --all               # только структура, без git
claude plugin validate ./plugins/<плагин> --strict   # каждый изменённый плагин
claude plugin validate . --strict                    # marketplace.json
```

`scripts/check-plugins.py` проверяет: поднята ли версия у затронутых плагинов и растёт ли она
монотонно; `name` скилла против имени каталога; semver и форму `dependencies`; существование
файлов по относительным ссылкам и по `${CLAUDE_PLUGIN_ROOT}`; соответствие `marketplace.json`
каталогам плагинов; ссылки на агентов, не определённых в плагине и его зависимостях (предупреждение).
Версии сравнивает и режим `--base <ref>` — для прогона на CI, где локальный хук мог быть не включён.

Чек-лист:

- [ ] `--strict` зелёный на изменённых плагинах и на marketplace
- [ ] `name` в `SKILL.md` совпадает с именем каталога
- [ ] нет битых относительных ссылок и `${CLAUDE_PLUGIN_ROOT}`-путей
- [ ] новое правило не дублирует текст из другого слоя
- [ ] нет захардкоженных версий пакетов
- [ ] `version` в `plugin.json` поднят по таблице выше — проверяется хуком автоматически
- [ ] хук проверен вручную — `echo '<json>' | python3 hooks/<хук>.py`
- [ ] новый агент действительно появился в списке (`claude plugin details`)

Хуки тестируются подачей события на stdin:

```bash
echo '{"session_id":"t","tool_name":"Edit","tool_input":{"file_path":"/x/lib/a.dart"}}' \
  | python3 plugins/v1rus-flutter/hooks/path-rules.py
```

### Публикация для команды

`marketplace.json` живёт в `.claude-plugin/` корня репозитория; каждая запись ссылается на
`./plugins/<имя>`. Дальше — обычный git: команда добавляет marketplace по URL репозитория, обновления
приезжают через `claude plugin marketplace update v1rus-dev`.

---

## Диагностика

| Симптом | Что смотреть |
|---|---|
| Плагин не появился | `claude plugin list` — установлен? включён? в том ли scope? |
| Агента нет в списке | Фронтматтер не разобрался как YAML — см. про блочный скаляр выше; проверить `claude plugin validate --strict` |
| Скилл не вызывается | `description` не покрывает формулировку; позвать явно `/<плагин>:<скилл>` и переписать описание |
| Правило не приходит перед правкой | Глобы `paths:` не совпали, или тело уже инжектилось в этой сессии (по дизайну — один раз) |
| Чартер не действует | Нет `python3` в `PATH`; проверить руками: `echo '{}' \| python3 plugins/v1rus-core/hooks/inject-charter.py` |
| Хук блокирует нужное | Сообщение блокировки называет причину и правило. Для работы на дефолтной ветке репозитория (docs, wiki) — `V1RUS_ALLOW_PROTECTED_BRANCH=1` |
| Изменения в плагине не подхватились | `claude plugin marketplace update v1rus-dev`, затем рестарт сессии; для версионного обновления — bump `version` в `plugin.json` |

---

## Состояние

Слои `v1rus-core`, `v1rus-kotlin`, `v1rus-compose`, `v1rus-kmp`, `v1rus-android`, `v1rus-flutter`,
`v1rus-dotnet`, `v1rus-typescript`, `v1rus-node`, `v1rus-react`, `v1rus-fullstack`, `v1rus-go`
проходят `scripts/check-plugins.py --all` и `claude plugin validate --strict`.

Дальше: обкатка `v1rus-android` и остальных новых слоёв на реальных проектах — слои написаны от
конвенций и официальных гайдов, а не сняты с живого кода, поэтому первые правки ожидаемы.
