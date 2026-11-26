---
name: lean-prove
description: Formalize a mathematical statement and its proof in Lean 4 + Mathlib, get it machine-checked on GitHub (repo thnastev/lean-proofs), and iterate until it passes. Use when the user types /lean-prove, or asks to prove, formalize, or verify something "in Lean".
---

# lean-prove: write a Lean proof and get it machine-checked

The user wants a **checked** proof, not just Lean code. Do the whole loop yourself,
without asking the user to do anything, and report only when it passes (or when you
are truly stuck).

Checker: GitHub Actions on `thnastev/lean-proofs` (Lean `v4.36.0`, Mathlib `v4.36.0`).
A proof passes only if it compiles, has no `sorry`/`admit`, declares no `axiom`, and
`#print axioms` shows only `propext`, `Classical.choice`, `Quot.sound`
(so no `native_decide`).

## Token

The GitHub token is in the project instructions/knowledge (a line like
`LEAN_GITHUB_TOKEN=github_pat_...`). Never print it, never put it in the proof
file, never repeat it in chat. If it is missing, tell the user in one line that the
token is not set up and point to the setup section of the repo README.

## Loop

1. **Understand the statement.** Restate it in one line of plain math. Pick precise
   types (`ℝ`, `ℤ`, `ℕ`; beware truncated `ℕ` subtraction/division). Pick a CamelCase
   module name, e.g. `SqrtTwoIrrational`.
2. **Write the file** `/tmp/<Name>.lean` (in the code sandbox), readable by a human:

   ```lean
   import Mathlib

   /-!
   # <Title>

   **Statement.** <plain-language statement>

   **Proof sketch.** <3–6 lines; mirrors the formal steps below>
   -/

   /-- <plain-math docstring> -/
   theorem <name> ... := by
     -- <comment per key step>
     ...

   #print axioms <name>
   ```

   Use structured steps (`have`, `calc`, `obtain ⟨x, hx⟩ := …`, `induction … with`),
   helper lemmas with docstrings for long proofs, and comments that match the sketch.
   Prefer Mathlib lemmas over re-proving standard facts. Mathlib names change often —
   if unsure, prefer robust tactics (`simp`, `omega`, `positivity`, `nlinarith`,
   `norm_num`, `ring`, `linarith`) over guessed lemma names. Never leave search
   tactics like `exact?`/`apply?` in the file.
3. **Check it** (takes ~2–6 minutes; just wait):

   ```bash
   python3 scripts/lean_check.py --token "$TOKEN" --name <Name> --file /tmp/<Name>.lean
   ```

   (`scripts/` is this skill's folder; copy the script into the sandbox if needed.)
   Set `TOKEN` from the project instructions in the same command, without echoing it.
4. **Read the verdict.** First line is `LEAN-CHECK: PASS` or `LEAN-CHECK: FAIL`,
   followed by the Lean messages (`Proofs/<Name>.lean:LINE:COL: error: …`).
   On FAIL: fix exactly what the errors say (unknown identifier → use another lemma
   name or prove it inline; unsolved goals → the message shows the remaining goal)
   and go back to step 3. Up to ~8 attempts; change strategy if the same step keeps
   failing.
5. **Report** (only after PASS): the final Lean file in a ```lean block, the informal
   proof in plain math, the axioms line, and the link the script prints
   (`https://github.com/thnastev/lean-proofs/blob/main/Proofs/<Name>.lean`).
   If you could not get it to pass, say so plainly, show the best attempt with the
   remaining `sorry` clearly marked and the exact open goal — never call it proven.

## Troubleshooting

- `HTTP 401/403` or connection errors to `api.github.com`: the code sandbox has no
  network access to GitHub, or the token expired. Tell the user in one line:
  enable network access for `api.github.com` in Settings → Capabilities (code
  execution), or regenerate the token.
- `no verdict after …s`: GitHub Actions is slow or disabled; give the user the CI
  link the script printed.
- Workflow finished without a verdict: Lean/Mathlib setup failed on GitHub's side;
  rerun once, then report the CI link.
