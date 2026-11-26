---
name: lean-prove
description: Formalize a mathematical statement and its proof in Lean 4 + Mathlib and machine-check it right here in the code sandbox, iterating until it passes. Use when the user types /lean-prove, or asks to prove, formalize, or verify something "in Lean".
---

# lean-prove: write a Lean proof and machine-check it in the sandbox

The user wants a **checked** proof, not just Lean code. Do the whole loop yourself
without asking the user to do anything; report when it passes (or when truly stuck).

The checker is `scripts/lean_check.py` in this skill's folder (Python stdlib only).
It runs a real Lean `v4.36.0` + Mathlib in the sandbox. A proof passes only if it
compiles with no errors, has no `sorry`/`admit`, declares no `axiom`, and every
declaration depends only on `propext`, `Classical.choice`, `Quot.sound`
(so `native_decide` fails too).

## 0. Start the install FIRST (it runs while you think)

Lean + Mathlib is ~2 GB to download and takes a few minutes, once per conversation.
Your very first action:

```bash
cp -r <this skill folder>/scripts /tmp/lean-skill 2>/dev/null; python3 /tmp/lean-skill/lean_check.py setup --background
```

Then write the proof while it installs. Check progress with
`python3 /tmp/lean-skill/lean_check.py status` (prints `READY`, `IN PROGRESS: …` or
`FAILED`). Don't poll in a tight loop: work on the proof, then check.

## 1. Write the proof

Restate the claim in one line of plain math. Pick exact types (`ℝ`, `ℤ`, `ℕ`;
`ℕ` subtraction/division truncate). Pick a CamelCase name. Write `/tmp/<Name>.lean`
so a human can read it:

```lean
import Mathlib

/-!
# <Title>

**Statement.** <plain-language statement>

**Proof sketch.** <3–6 lines; mirrors the formal steps below>
-/

/-- <plain-math docstring> -/
theorem <name> ... := by
  -- <short comment per key step>
  ...
```

Use structured steps (`have`, `calc`, `obtain ⟨x, hx⟩ := …`, `induction … with`),
helper lemmas with docstrings for long proofs. Prefer robust tactics (`simp`,
`omega`, `ring`, `linarith`, `nlinarith`, `positivity`, `norm_num`, `field_simp`,
`aesop`, `decide`) and well-known Mathlib lemmas. Never leave `exact?`/`apply?` in the
final file. Always `import Mathlib` (the sandbox has all of it).

## 2. Check, fix, repeat

```bash
python3 /tmp/lean-skill/lean_check.py check /tmp/<Name>.lean
```

Last line is `LEAN-CHECK: PASS` or `LEAN-CHECK: FAIL`; above it are Lean's messages
(`<Name>.lean:LINE:COL: error: …`) and the axioms of each declaration.
On FAIL, fix exactly what Lean reports (unknown identifier → different lemma or
prove it inline; unsolved goals → the message shows the remaining goal; a
counterexample from `omega`/`decide` may mean the statement itself is false — then
tell the user). Each check takes seconds, so iterate freely; tactic experiments in a
scratch file are cheap (`/tmp/Scratch.lean` with `example … := by …`). Change
strategy if the same step fails 3 times.

## 3. Report (only after PASS)

1. The final Lean file in a ```lean block.
2. The informal proof in plain math (matching the formal steps).
3. The verdict lines (`PASS` and the axioms list) as evidence.
4. If `/mnt/user-data/outputs` exists, copy the file there so the user can download it.

If you cannot get it to pass, say so plainly: show the best attempt with the open
step marked `sorry`, the exact remaining goal, and never call it proven.

## Troubleshooting

- `status` says FAILED with a network/HTTP error (403, "proxy", "connection"): the
  sandbox can't download from GitHub. Tell the user, in one line, to allow these
  domains in Settings → Capabilities (code execution network access):
  `github.com`, `api.github.com`, `release-assets.githubusercontent.com`,
  `objects.githubusercontent.com` (or allow all domains). Then rerun setup.
- "No space left" / killed: the sandbox is too small; say so plainly.
- `lean` killed or very slow on a big file: split it into smaller lemmas.
