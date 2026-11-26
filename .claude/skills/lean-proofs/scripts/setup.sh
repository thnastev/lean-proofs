#!/usr/bin/env bash
# Idempotent (re)install of the Lean 4 + Mathlib environment. Safe to re-run.
set -euo pipefail
ROOT="${LEAN_PROJECT_PATH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}"
export PATH="$HOME/.elan/bin:$HOME/.local/bin:$PATH"
if ! command -v elan >/dev/null; then
  curl -sSfL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y --default-toolchain none
fi
cd "$ROOT"
if [ -f lean-toolchain ]; then elan toolchain install "$(cat lean-toolchain)"; else elan default stable; fi
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
[ -f lakefile.toml ] || lake init Proofs math
lake exe cache get
lake build
uvx lean-lsp-mcp --help >/dev/null && echo "lean-lsp-mcp OK"
grep -q lean-lsp .mcp.json 2>/dev/null || claude mcp add -s project lean-lsp \
  -e PATH="$HOME/.elan/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin" -- uvx lean-lsp-mcp
echo "Setup complete: $(lean --version)"
