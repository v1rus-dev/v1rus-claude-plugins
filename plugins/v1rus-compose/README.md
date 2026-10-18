# v1rus-compose

Everything v1rus holds true for a **Compose application regardless of target**. Compose
Multiplatform and native-Android Jetpack Compose share the same runtime, the same compiler plugin and
the same UI conventions, so they share this layer. Depends on `v1rus-kotlin`, which depends on
`v1rus-core` — installing this one pulls in both.

```
/plugin install v1rus-compose@v1rus
```

Normally you do not install it directly: `v1rus-kmp` and `v1rus-android` both depend on it and pull
it in. Install it on its own only for a Compose project that is neither — a desktop-only or
Compose-for-Web surface.

## What it contains

### Conventions

| Skill | Covers |
|---|---|
| `compose-ui-conventions` | The pre-review checklist: screen states, back navigation in every state, touch targets, `contentDescription`, theme tokens only, no raw enum in UI, list keys, `@Immutable` |
| `compose-screen-architecture` | The reference screen: Destination ⇄ Screen ⇄ Part split, state hoisting, sections, previews (+ five reference documents) |
| `compose-file-organisation` | One composable per file with a preview; the `ModelUi` exception |
| `mvi-presentation` | Store-style ViewModel over State/Intent/Effect, single `ModelUi` file |
| `compose-navigation-patterns` | Typed routes, serializer registration, feature isolation, dialogs and bottom sheets as destinations, result passing |
| `compose-animations` | Every state-driven change is animated; API mapping, `transitionSpec` recipes, `contentKey`, the text-field-in-`AnimatedContent` trap |
| `compose-clickability` | Clip before clickable, ripple containment, touch-target sizing, interaction sources, accessibility roles |
| `di-koin-conventions` | Initialisation, where a binding goes, constructor injection, `getAll` + `bind` |
| `localisation-and-strings` | Resources for everything user-visible including fallbacks; server text verbatim; closed sets mapped to localised labels; locales kept in sync |

### Compose performance and stability

Twenty-six deep-dive skills: stability inference and strong skipping, recomposition tracing and
debugging, lazy-layout optimisation and prefetch, deferred state reads, effect usage, modifier-chain
ordering, `Modifier.Node` migration, subcomposition pitfalls, `derivedStateOf`, flow collection,
baseline profiles, R8 configuration, release-mode measurement, hot reload, and CI stability
enforcement. `auditing-compose-performance` is the entry point that sequences the rest.

These are shared deliberately. R8, Baseline Profiles, Macrobenchmark and Layout Inspector all act on
an Android application — and a Compose Multiplatform project ships one too, so none of them is
native-Android-only.

### Path-scoped rules

`rules/compose-files.md` fires on edits under feature, design-system, presentation or UI packages.
Delivered by `hooks/path-rules.py`.

### Agents

| Agent | Role |
|---|---|
| `compose-developer` | Writes Compose UI and the MVI presentation layer — screens, composables, previews, theme usage, navigation, animation, the store ViewModel. Not the logic layer, which is `v1rus-kotlin:kotlin-engineer`. |

`references/compose-rules.md` is the deep material that agent reads, addressed as
`${CLAUDE_PLUGIN_ROOT}/references/compose-rules.md`. Its multiplatform-only addendum is the Compose
Multiplatform UI section of the `v1rus-kmp:kmp-conventions` skill.

## Where the target-specific parts live

This layer never assumes a target. Anything that does belongs one layer up:

| Concern | Layer |
|---|---|
| `commonMain` / `expect` / `actual`, iOS framework boundary, CMP version alignment | `v1rus-kmp` |
| Gradle module graph of an Android app, manifest, `Context` and lifecycle, Room + Ktor-on-OkHttp + DataStore | `v1rus-android` |
| Kotlin style, coroutines, Gradle | `v1rus-kotlin` |
| Gates, review, testing bands, source trust | `v1rus-core` |

A skill here that names a target-specific detail states the condition explicitly ("on a Compose
Multiplatform project, additionally …") rather than assuming one.

## What deliberately stays in the project

A project's **concrete** architecture — exact module paths, the real names of its navigator, store,
theme and result store, its Gradle task names — stays in that project's own `.claude/rules/` and
`CLAUDE.md`. The plugin carries the pattern and the rule; the project carries the names.
