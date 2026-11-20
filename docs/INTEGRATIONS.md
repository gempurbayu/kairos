# Agent harness integrations

The project exposes one local MCP server over stdio. Install it once, then point any MCP-compatible harness at the same `youtube-clipper-mcp` executable. The examples below use the path printed by the setup script.

## 1. Install

Install FFmpeg first. From the project directory:

macOS/Linux:

```bash
./scripts/setup.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
```

The default works without API keys and uses local transcription plus offline highlight scoring. For Gemini selection, add `GEMINI_API_KEY=...` to the project's `.env` file. Never commit `.env`.

## Codex

Codex CLI, its IDE extension, and the Codex desktop app share MCP configuration. With Codex CLI, add the server using the absolute path printed during setup:

```bash
codex mcp add youtube-auto-clipper -- \
  /absolute/path/to/youtube-auto-clipper/.venv/bin/youtube-clipper-mcp
```

On Windows, use the absolute path to `.venv/Scripts/youtube-clipper-mcp.exe`. Or add this to `~/.codex/config.toml`:

```toml
[mcp_servers.youtube_auto_clipper]
command = "/absolute/path/to/youtube-auto-clipper/.venv/bin/youtube-clipper-mcp"
```

Then restart/reload Codex and check `/mcp` or `codex mcp list`.

## Hermes Agent

Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  youtube_auto_clipper:
    command: "/absolute/path/to/youtube-auto-clipper/.venv/bin/youtube-clipper-mcp"
    args: []
    timeout: 3600
```

Restart Hermes. The tools should appear under the `mcp-youtube_auto_clipper` toolset.

## OpenClaw

Add an MCP server in Control UI → Settings → MCP, select **Stdio**, and enter the absolute executable path printed by setup. For config-file setup, add this to the OpenClaw configuration (JSON5):

```json5
{
  mcp: {
    servers: {
      youtube_auto_clipper: {
        command: "/absolute/path/to/youtube-auto-clipper/.venv/bin/youtube-clipper-mcp",
        args: [],
        cwd: "/absolute/path/to/youtube-auto-clipper",
        enabled: true,
      },
    },
  },
}
```

Verify the connection with `openclaw mcp status` or `openclaw mcp doctor youtube_auto_clipper --probe`.

## Other MCP clients

Choose **stdio/local command** as the transport and use the same absolute `youtube-clipper-mcp` path. The server provides `transcribe_local_video`, `find_highlights`, and `generate_clips` tools. YouTube downloads stay disabled unless the caller explicitly sets `allow_download: true`.
