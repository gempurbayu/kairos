#!/usr/bin/env sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
UV_BIN="${UV:-uv}"

if ! command -v "$UV_BIN" >/dev/null 2>&1; then
  echo "uv is required. Install it with: brew install uv" >&2
  exit 1
fi

# Release the old distribution's command names before installing the Kairos package.
"$UV_BIN" tool uninstall youtube-auto-clipper >/dev/null 2>&1 || true
"$UV_BIN" tool install --editable "$PROJECT_ROOT"

printf '\nKairos installation complete. Use this same MCP command in every harness:\nkairos-mcp\n'
printf 'If the harness cannot find it, run: %s tool update-shell\n' "$UV_BIN"
printf 'Optional: create %s/.env and set GEMINI_API_KEY for Gemini highlight selection.\n' "$PROJECT_ROOT"

TOOL_BIN_DIR="$("$UV_BIN" tool dir --bin)"
if ! "$TOOL_BIN_DIR/kairos" doctor; then
  printf '\nKairos is installed, but the machine needs the fixes shown above before rendering.\n' >&2
  exit 1
fi
