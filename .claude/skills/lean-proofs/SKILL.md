---
name: lean-proofs
description: Write and machine-check formal proofs in Lean 4 + Mathlib, in a form the user can also read. Use whenever the user asks to prove, formalize, or verify a mathematical statement, or when working on any .lean file in this repo. Also use to (re)install the Lean environment if `lake`/`lean` are missing.
---

# Lean 4 + Mathlib proofs

Project root: the repo root (three levels above this skill folder; `/home/user` in the first session) (Lake project `Proofs`, Lean `v4.36.0`, Mathlib `v4.36.0`).
Toolchain lives in `~/.elan/bin` — prefix commands with `export PATH=$HOME/.elan/bin:$PATH`.

## 0. Environment check (first use in a session)

```bash
export PATH=$HOME/.elan/bin:$PATH; lake --version || bash .claude/skills/lean-proofs/scripts/setup.sh   # from the repo root
```

`setup.sh` is idempotent: installs elan + the pinned toolchain, uv, pulls the Mathlib
binary cache (`lake exe cache get`, ~9k files — never build Mathlib from source),
runs `lake build`, and registers the `lean-lsp` MCP server in `.mcp.json`.

## 1. Workflow

1. **Statement first.** Write the theorem statement with a docstring stating it in plain
   math, and prove it with `sorry` temporarily. Compile to confirm the *statement*
   typechecks and means what the user asked (check coercions: `ℕ` subtraction/division
   truncate; prefer `ℝ`/`ℤ` when the math does).
2. **Prove interactively.** If the `lean-lsp` MCP tools are available, use them:
   - `lean_goal` (goal state at a line) — inspect before/after each tactic
   - `lean_diagnostic_messages` — errors/warnings for the file
   - `lean_multi_attempt` — try several tactics at one spot
   - `lean_loogle`, `lean_leansearch`, `lean_local_search`, `lean_hover_info` — find Mathlib lemmas
   Without MCP: `lake env lean File.lean` (from the repo root), and use `exact?`, `apply?`,
   `#check`, `#loogle`-style search by grepping `.lake/packages/mathlib/Mathlib`.
3. **Verify strictly** (mandatory before claiming a proof is done):
   ```bash
   .claude/skills/lean-proofs/scripts/verify.sh File.lean
   ```
   It must print `PASS`. It fails on compile errors, any `sorry`/`admit`, a user-declared
   `axiom`, or any axiom beyond `propext`, `Classical.choice`, `Quot.sound`
   (so `native_decide` is rejected too).
4. **Report** the verifier output honestly. If a proof can't be finished, say exactly which
   step is open and leave that `sorry` clearly marked — never present it as complete.

## 2. Make proofs readable for the user

The user reads these proofs. Optimize for a mathematician skimming the file:

- Module docstring `/-! # Title ... -/` with the informal statement and a 3–6 line
  **informal proof sketch** that matches the formal steps.
- One docstring per theorem/lemma, in plain math.
- Split long proofs into named helper lemmas, each with its own docstring.
- Prefer structured tactics that mirror paper proofs: `have h : … := by …`, `calc`,
  `obtain ⟨x, hx⟩ := …`, `rcases`, `induction n with | zero => … | succ n ih => …`,
  `constructor` / `refine ⟨_, _⟩`. Add a short `-- comment` before each key step.
- Avoid opaque one-liners (a bare `aesop`/`omega`/`simp` closing a big goal) unless the
  step is genuinely routine; when used, comment what they are discharging.
- Put `#print axioms MainTheorem` at the end of the file as the human-checkable certificate.
- One topic per file under `Proofs/` (e.g. `Proofs/SqrtTwo.lean`), imported from
  `Proofs.lean` so `lake build` checks everything.

## 3. Template

```lean
import Mathlib

/-!
# Sum of two even integers is even

**Statement.** If `a` and `b` are even, then `a + b` is even.

**Proof sketch.** Write `a = k + k`, `b = m + m`; then `a + b = (k + m) + (k + m)`.
-/

/-- The sum of two even integers is even. -/
theorem even_add_even' (a b : ℤ) (ha : Even a) (hb : Even b) : Even (a + b) := by
  -- unpack the witnesses
  obtain ⟨k, rfl⟩ := ha
  obtain ⟨m, rfl⟩ := hb
  -- `k + m` is the witness
  exact ⟨k + m, by ring⟩

#print axioms even_add_even'
```

## 4. Troubleshooting

- `unknown package 'Mathlib'` / very slow first compile → `lake exe cache get` in the repo root.
- `lake: command not found` → `export PATH=$HOME/.elan/bin:$PATH`, or run `setup.sh`.
- Lemma names changed → search with `lean_loogle`/`lean_leansearch` or
  `grep -rn "theorem name_fragment" .lake/packages/mathlib/Mathlib`.
- MCP `lean-lsp` tools missing → they load at session start after approving the
  project server in `.mcp.json`; fall back to `lake env lean` + `verify.sh` meanwhile.
