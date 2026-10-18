---
name: ts-type-design
description: |-
  Use when modelling domain types, unions and exhaustiveness, branded types, replacing enum/any/non-null assertion/as, designing generics or API signatures, using satisfies, or preparing a library's public types.
  Do NOT use for runtime validation of external input (ts-boundaries) or lint/tsconfig configuration.
---

# Type design

Read `${CLAUDE_PLUGIN_ROOT}/rules/ts-types.md` (type section) and apply it; it is also injected when you edit source files.
- Start from the states the domain really has; encode them as a tagged union; add an exhaustive `switch` with a `never` check.
- Replace `any`/`!`/`as` by narrowing or a validated constructor, not by a bigger cast.
- Libraries: exported functions get explicit return types; derive types from schemas/values.
- Check the result with the project's typecheck script and, for tricky types, a throwaway `// @ts-expect-error` probe.
