#!/usr/bin/env sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

"$PYTHON_BIN" -m venv "$PROJECT_ROOT/.venv"
"$PROJECT_ROOT/.venv/bin/python" -m pip install --upgrade pip
"$PROJECT_ROOT/.venv/bin/python" -m pip install -e "$PROJECT_ROOT"

printf '\nSetup complete. MCP server command:\n%s\n' "$PROJECT_ROOT/.venv/bin/youtube-clipper-mcp"
printf 'Optional: create %s/.env and set GEMINI_API_KEY for Gemini highlight selection.\n' "$PROJECT_ROOT"
