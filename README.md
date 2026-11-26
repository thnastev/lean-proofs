# lean-proofs

Formal proofs written by Claude in **Lean 4 + Mathlib**, each machine-checked, and
written so that a mathematician can read them.

- Lean `v4.36.0`, Mathlib `v4.36.0` (pinned in `lean-toolchain` / `lakefile.toml`)
- Proofs live in `Proofs/` (one topic per file); `Test.lean` is the setup smoke test.

## How to trust a proof here

A proof counts as done only if **all** of these hold:

1. It compiles with zero errors.
2. It contains no `sorry` / `admit`, and declares no new `axiom`.
3. `#print axioms TheoremName` lists only Lean's three standard axioms:
   `propext`, `Classical.choice`, `Quot.sound` (so no `sorryAx` and no `native_decide`).

`.claude/skills/lean-proofs/scripts/verify.sh` checks all three. GitHub Actions
(**Verify proofs**) re-runs it on every push, independently of Claude. A green check
on a commit means every `.lean` file in it passed.

What remains for you to check by eye is that **the theorem statement says what you
meant**. Each file opens with a plain-language statement and an informal proof sketch
to make that easy.

## Checking locally

```bash
lake exe cache get          # download precompiled Mathlib (never build it from source)
lake build                  # compile everything imported from Proofs.lean
.claude/skills/lean-proofs/scripts/verify.sh Test.lean Proofs/*.lean
```

Fresh machine/container: `bash .claude/skills/lean-proofs/scripts/setup.sh`.

## For Claude

Rules are in `CLAUDE.md`; the workflow is the `lean-proofs` skill in
`.claude/skills/lean-proofs/SKILL.md`. The `lean-lsp` MCP server (`.mcp.json`) gives
live goal states and diagnostics.
