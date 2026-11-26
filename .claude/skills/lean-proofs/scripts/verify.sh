#!/usr/bin/env bash
# Strictly verify Lean files: compile against Mathlib, then reject any error,
# any `sorry`/`admit`, any user-declared `axiom`, and any non-standard axiom.
# Usage: verify.sh File1.lean [File2.lean ...]   (run from anywhere)
set -uo pipefail
export PATH="$HOME/.elan/bin:$HOME/.local/bin:$PATH"
ROOT="${LEAN_PROJECT_PATH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}"
cd "$ROOT" || { echo "no project at $ROOT"; exit 2; }
[ $# -ge 1 ] || { echo "usage: verify.sh File.lean ..."; exit 2; }
fail=0
for f in "$@"; do
  echo "== $f"
  [ -f "$f" ] || { echo "  FAIL: file not found"; fail=1; continue; }
  # Append `#print axioms` for every theorem/lemma so sorry can't hide anywhere.
  tmp="$(mktemp "$ROOT/.verify_XXXX.lean")"
  cat "$f" > "$tmp"
  printf '\n' >> "$tmp"
  ns=""
  grep -oE '^(private |protected )?(noncomputable )?(theorem|lemma|def|instance|abbrev) +[^ :({\[]+' "$f" \
    | awk '{print $NF}' | while read -r n; do echo "#print axioms $n"; done >> "$tmp"
  out="$(lake env lean "$tmp" 2>&1 | grep -v canonicalize)"
  out="${out//$tmp/$f}"   # show the real file name in messages
  rm -f "$tmp"
  bad=0
  if echo "$out" | grep -qE '(^|: )error'; then echo "  FAIL: compile errors"; bad=1; fi
  if echo "$out" | grep -qE "declaration uses .sorry.|sorryAx"; then echo "  FAIL: contains sorry"; bad=1; fi
  if grep -nE '(^|[^A-Za-z_])(sorry|admit)([^A-Za-z_]|$)' "$f" | grep -v -- '--' >/dev/null; then echo "  FAIL: literal sorry/admit in source"; bad=1; fi
  if grep -nE '^\s*axiom ' "$f" >/dev/null; then echo "  FAIL: file declares its own axiom"; bad=1; fi
  if echo "$out" | grep -E 'depends on axioms' | grep -vqE 'axioms: \[((propext|Classical\.choice|Quot\.sound)(, )?)*\]'; then
    echo "  FAIL: non-standard axioms (sorryAx, native_decide, custom axiom...) - see list below"; bad=1; fi
  echo "$out" | sed 's/^/  | /'
  [ $bad -eq 0 ] && echo "  PASS: compiles, no sorry, standard axioms only" || fail=1
done
exit $fail
