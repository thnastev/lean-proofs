# Lean 4 + Mathlib proof workspace

This directory is a Lake project (`Proofs`) on Lean `v4.36.0` with Mathlib `v4.36.0`.
For any proof / formalization work, follow the `lean-proofs` skill
(`.claude/skills/lean-proofs/SKILL.md`).

## Hard rules

- **Always verify every `.lean` file you write or change** — with the `lean-lsp` MCP tools
  (`lean_diagnostic_messages`, `lean_goal`) while working, and with
  `.claude/skills/lean-proofs/scripts/verify.sh <file>` (or `lake build`) before finishing.
- **Never leave `sorry` (or `admit`) in a proof you present as complete.** No new `axiom`
  declarations, no `native_decide`. `#print axioms` must show only
  `propext`, `Classical.choice`, `Quot.sound`.
- Never claim a proof checks without having run the verifier in this session and seen `PASS`.
  If something can't be proven, say so plainly and mark the open `sorry`.
- Never build Mathlib from source: run `lake exe cache get` if Mathlib `.olean`s are missing.
- Write proofs to be read by a human: docstrings, informal proof sketch, structured
  `have`/`calc`/`obtain` steps with short comments.

## Commands

```bash
export PATH=$HOME/.elan/bin:$PATH        # elan/lean/lake
lake build                               # check everything imported from Proofs.lean
lake env lean Test.lean                  # check a single file
.claude/skills/lean-proofs/scripts/verify.sh Test.lean   # strict check (sorry/axioms)
bash .claude/skills/lean-proofs/scripts/setup.sh         # reinstall in a fresh container
```
