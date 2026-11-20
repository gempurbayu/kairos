$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$UvExe = if ($env:UV) { $env:UV } else { "uv" }

if (-not (Get-Command $UvExe -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/"
}

& $UvExe tool uninstall youtube-auto-clipper *> $null
$LASTEXITCODE = 0
& $UvExe tool install --editable $ProjectRoot
if ($LASTEXITCODE -ne 0) { throw "uv tool install failed with exit code $LASTEXITCODE" }

Write-Host "Kairos installation complete. Use this same MCP command in every harness: kairos-mcp"
Write-Host "If the harness cannot find it, run: uv tool update-shell"
Write-Host "Optional: create $ProjectRoot\.env and set GEMINI_API_KEY for Gemini highlight selection."

$ToolBinDir = & $UvExe tool dir --bin
if ($LASTEXITCODE -ne 0) { throw "Unable to locate the uv tool bin directory" }
& (Join-Path $ToolBinDir "kairos.exe") doctor
if ($LASTEXITCODE -ne 0) { throw "Kairos is installed, but the machine needs the fixes shown above before rendering" }
