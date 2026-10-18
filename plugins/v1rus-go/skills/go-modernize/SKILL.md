---
name: go-modernize
description: |-
  Modernize Go code after a go-line or toolchain bump, or when code uses pre-1.22 idioms (loop-variable copies, interface{}, sort.Slice, ioutil, 3-clause counting loops) using go fix.
  Use when: the go directive is being raised, the user asks to modernize or clean up legacy idioms.
  Not for: bug fixes or feature work (minimal-diff rule: do not mix modernization into them); raising the go line without an explicit plan-stage decision.
---

Follow [reference/modernize.md](reference/modernize.md). Modernization is its own change, never bundled with behavior changes.
