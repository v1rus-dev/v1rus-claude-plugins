# JSDoc and checkJs

- Use mainstream JSDoc-TS: `@param {T} x`, `@returns {T}`, `@type`, `@typedef`, `@template T`, `@satisfies`, `@import { Foo } from './foo.js'` (avoids runtime imports in JS). Put non-trivial types in `.d.ts` files or a typedef module.
- TypeScript 7 tightened JS checking (per its release notes): no `@enum`, no `@class` constructor magic, no postfix `!`, no Closure-style function types, no values used as types. Avoid them in new code.
- Migration per file: `// @ts-check` header. Use `// @ts-expect-error` with a reason, not `@ts-ignore`.
- Typed ESLint only applies to files in a tsconfig program; apply `disableTypeChecked` to the rest.
- Migrate to `.ts` when JSDoc generics/overloads become unreadable, when publishing rich declarations, or when type stripping makes `.ts` free (check the Node line). Rename file by file with `allowJs` on, keep `erasableSyntaxOnly` so files stay valid JS-with-types, no behaviour change in the same commit. A library may stay JS and still emit `.d.ts` with `tsc --emitDeclarationOnly`.
