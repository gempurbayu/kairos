#!/usr/bin/env sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
UV_BIN="${UV:-uv}"

if ! command -v "$UV_BIN" >/dev/null 2>&1; then
  echo "uv is required. Install it with: brew install uv" >&2
  exit 1
fi

"$UV_BIN" tool install --editable "$PROJECT_ROOT"

printf '\nSetup complete. Use this same MCP command in every harness:\nyoutube-clipper-mcp\n'
printf 'If the harness cannot find it, run: %s tool update-shell\n' "$UV_BIN"
printf 'Optional: create %s/.env and set GEMINI_API_KEY for Gemini highlight selection.\n' "$PROJECT_ROOT"
