$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonExe = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

& $PythonExe -m venv (Join-Path $ProjectRoot ".venv")
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e $ProjectRoot

Write-Host "Setup complete. MCP server command:"
Write-Host (Join-Path $ProjectRoot ".venv\Scripts\youtube-clipper-mcp.exe")
Write-Host "Optional: create $ProjectRoot\.env and set GEMINI_API_KEY for Gemini highlight selection."
