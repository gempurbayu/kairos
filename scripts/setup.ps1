$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$UvExe = if ($env:UV) { $env:UV } else { "uv" }

if (-not (Get-Command $UvExe -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/"
}

& $UvExe tool install --editable $ProjectRoot
if ($LASTEXITCODE -ne 0) { throw "uv tool install failed with exit code $LASTEXITCODE" }

Write-Host "Setup complete. Use this same MCP command in every harness: youtube-clipper-mcp"
Write-Host "If the harness cannot find it, run: uv tool update-shell"
Write-Host "Optional: create $ProjectRoot\.env and set GEMINI_API_KEY for Gemini highlight selection."
