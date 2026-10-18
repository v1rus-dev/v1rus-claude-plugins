---
name: ts-type-modelling
description: "How to model a domain in TypeScript types so illegal states cannot be constructed: discriminated unions instead of bags of optional fields, the exhaustive switch with a `never` guard that turns a new variant into a build error, `satisfies` versus `as` versus a widening annotation, branded/opaque types so a UserId cannot be passed where an OrderId is expected, readonly and `as const` and the fact that readonly is shallow, unions of string literals instead of enums, when a generic earns its type parameter and when it is an `any` with ceremony, and the traps in Omit, Partial, overloads and interface declaration merging. Load when designing a domain model, state shape or public function signature, when a type has grown optional fields that are only valid in certain combinations, when choosing between an enum, a union and a const object, when reaching for `as`, or when reviewing whether a type actually prevents the bug it claims to. Not for validating external data at runtime (`ts-boundaries-validation`) or for error types specifically (`ts-error-handling`)."
---

# Type Modelling

The goal is not "everything has a type". The goal is that the wrong program does not compile.

## Make illegal states unrepresentable

The default failure mode is a record of optional fields whose valid combinations live only in the
author's head:

```ts
// Permits { loading: true, error: 'x', data: [...] } — a state that cannot happen,
// and every consumer must defend against it anyway.
type State = { loading?: boolean; error?: string; data?: User[] };
```

```ts
// Four states, each carrying exactly what it has and nothing it does not.
type State =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'failed'; error: AppError }
  | { kind: 'loaded'; users: readonly User[] };
```

The discriminant is a literal field present on **every** member, with the same name. Narrowing on it
is what gives the consumer `users` without a check and without a `!`.

Same principle beyond state: a function taking `(a?: X, b?: Y)` where exactly one is required takes
a union of two argument shapes instead.

## Exhaustiveness — the `never` guard

A `switch` over a union must be provably complete, or it silently stops being complete the day
someone adds a variant:

```ts
const assertNever = (value: never): never => {
  throw new Error(`Unhandled variant: ${JSON.stringify(value)}`);
};

switch (state.kind) {
  case 'idle': return renderIdle();
  case 'loading': return renderSpinner();
  case 'failed': return renderError(state.error);
  case 'loaded': return renderList(state.users);
  default: return assertNever(state);
}
```

- `default: throw new Error('unknown state')` is **not** a guard. It compiles forever, whatever the
  union grows into. The point is the compile error, not the runtime throw.
- The runtime throw still matters: the value can be a variant the compiler did not know about
  (`ts-boundaries-validation`).
- `@typescript-eslint/switch-exhaustiveness-check` enforces this mechanically — see
  `ts-lint-and-format`.
- The same discipline applies to `if/else if` chains over a union; if a chain is long enough to need
  it, it wanted to be a `switch`.

## `satisfies`, annotation, `as` — three different things

```ts
const routes = {
  home: '/',
  user: '/users/:id',
} satisfies Record<string, `/${string}`>;
```

- **Annotation** (`const routes: Record<string, string> = …`) checks *and widens*. `routes.home` is
  now `string`, and `routes.typo` is a legal read. You lost the literal types.
- **`as`** checks nothing meaningful and asserts. It is how a typo survives to runtime.
- **`satisfies`** checks the value against the type and keeps the inferred narrow shape. It is the
  right tool for config objects, route maps, lookup tables, theme tokens and default values.

Use `as` only where there is genuinely no other expression form: narrowing a literal you just
constructed, or the `as const` assertion. Never `as` to bridge two shapes that disagree — that is a
mapper's job.

## Branded types for identifiers

Every id is a `string`, so every id is interchangeable, so eventually an `orderId` is passed where a
`userId` belongs and the query returns nothing:

```ts
declare const brand: unique symbol;
type Brand<T, B extends string> = T & { readonly [brand]: B };

export type UserId = Brand<string, 'UserId'>;
export type OrderId = Brand<string, 'OrderId'>;
```

The rule that makes it worth the ceremony: **there is exactly one way to produce a branded value**,
and it is a function that validates — the parse at the boundary (`ts-boundaries-validation`) or an
explicit constructor. If the codebase is full of `id as UserId`, the brand buys nothing but noise.

Brand the identifiers that are actually confusable and the primitives that carry a unit or an
invariant (`Cents`, `Email`, `IsoDate`). Do not brand every string in the domain.

## Immutability

- `readonly` on properties and `readonly T[]` (or `ReadonlyArray<T>`) on collections, by default, for
  anything the receiver is not meant to change. It costs nothing at runtime and documents ownership.
- `as const` for literal data: it freezes the inferred type, not the object. `Object.freeze` is the
  runtime half, and it is rarely needed.
- **`readonly` is shallow.** `readonly user: User` does not stop `user.name = 'x'`. Say so in the
  type (`Readonly<T>` recursively where it matters) rather than assuming.
- Prefer returning a new value to mutating a parameter. A function that mutates its argument
  announces it in the name, or takes ownership explicitly.

## Enums, unions and const objects

Prefer a **union of string literals** (`type Status = 'draft' | 'sent' | 'paid'`) or an `as const`
object when a runtime value list is needed:

```ts
export const Status = { Draft: 'draft', Sent: 'sent', Paid: 'paid' } as const;
export type Status = (typeof Status)[keyof typeof Status];
```

Why not `enum`: it emits a runtime object that cannot be tree-shaken, its members are nominal in ways
that surprise (a plain `'draft'` is not assignable to a string enum member), and `const enum` is
incompatible with `isolatedModules` and single-file transpilers. A union is erased entirely, narrows
naturally, and interoperates with parsed data.

## Generics that earn their place

**A type parameter that appears exactly once in the signature is not doing anything.** It is an
`any` the reader has to decode:

```ts
// T appears once — this is `(value: unknown) => void` with extra steps.
function log<T>(value: T): void;
```

A parameter earns its place when it links two positions: input to output, argument to argument,
or property to return. Then constrain it (`<T extends { id: string }>`) so the body can rely on
something, and let it be inferred at the call site rather than requiring an explicit argument.

Signs the generic went too far: a signature needing a comment to read, conditional types three levels
deep, `infer` used to reconstruct something the caller already knew. A slightly less precise type
that a teammate can read beats a precise one they will `as any` past.

## Utility-type traps

- **`Omit<T, K>` does not check `K` against `keyof T`.** `Omit<User, 'naem'>` is a valid type that
  removes nothing, silently. Prefer `Omit<User, keyof Pick<User, 'name'>>` where it matters, or a
  small `StrictOmit` helper, and be suspicious of `Omit` in a diff that renames fields.
- **`Omit` and `Partial` do not distribute over a union.** Applying them to a discriminated union
  collapses it and destroys the narrowing. Map over the union explicitly.
- **`Partial<T>` as a function parameter** is usually a modelling failure: it says every field is
  optional, which is almost never true. Model the actual patch shape.
- **`interface` declarations merge.** Two `interface Config` in scope silently become one; `type`
  aliases collide loudly. Use `interface` for a contract meant to be extended or augmented, `type`
  for unions, mapped types, and everything else. Never use `interface` for a shape that must not be
  reopened by a consumer.
- **Overloads are unchecked against the implementation.** The implementation signature is invisible
  to callers and the compiler only loosely relates the two, so a wrong overload is a runtime bug with
  a green build. Prefer a union parameter or a generic; keep overloads for genuinely distinct
  argument arities.
