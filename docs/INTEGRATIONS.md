# Agent harness integrations

The project exposes one local MCP server over stdio. Install it once as a global CLI, then every MCP-compatible harness can launch the same command name: `youtube-clipper-mcp`. This avoids per-harness virtual-environment paths. Each harness still needs a server registration because its configuration format is different.

## 1. Install

Install FFmpeg and [uv](https://docs.astral.sh/uv/getting-started/installation/) first. From the project directory:

macOS/Linux:

```bash
./scripts/setup.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
```

The setup installs this project as an editable uv tool, so source updates remain visible to the installed command. The default works without API keys and uses local transcription plus offline highlight scoring. For Gemini selection, add `GEMINI_API_KEY=...` to the project's `.env` file. Never commit `.env`.

If the harness cannot resolve `youtube-clipper-mcp`, run `uv tool update-shell`, reopen the harness, and try again. Use an absolute executable path only for a harness that does not inherit the user's PATH.

## Codex

Codex CLI, its IDE extension, and the Codex desktop app share MCP configuration. With Codex CLI, add the MCP server once:

```bash
codex mcp add youtube-auto-clipper -- \
  youtube-clipper-mcp
```

Or add this to `~/.codex/config.toml`:

```toml
[mcp_servers.youtube_auto_clipper]
command = "youtube-clipper-mcp"
```

Then restart/reload Codex and check `/mcp` or `codex mcp list`.

## Hermes Agent

Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  youtube_auto_clipper:
    command: "youtube-clipper-mcp"
    args: []
    timeout: 3600
```

Restart Hermes. The tools should appear under the `mcp-youtube_auto_clipper` toolset.

## OpenClaw

Add an MCP server in Control UI → Settings → MCP, select **Stdio**, and enter `youtube-clipper-mcp` as the command. For config-file setup, add this to the OpenClaw configuration (JSON5):

```json5
{
  mcp: {
    servers: {
      youtube_auto_clipper: {
        command: "youtube-clipper-mcp",
        args: [],
        enabled: true,
      },
    },
  },
}
```

Verify the connection with `openclaw mcp status` or `openclaw mcp doctor youtube_auto_clipper --probe`.

## Other MCP clients

Choose **stdio/local command** as the transport and use `youtube-clipper-mcp`. The server provides `transcribe_local_video`, `find_highlights`, and `generate_clips` tools. YouTube downloads stay disabled unless the caller explicitly sets `allow_download: true`.

## Install the skill in multiple agents

The repo's `SKILL.md` follows the portable Agent Skills format. After this repository has a public GitHub remote, users can install that skill into compatible agents with the Vercel Skills CLI, which detects supported agents and links one canonical skill copy:

```bash
npx skills add <owner>/<repo> --skill youtube-clipper -g
```

This installs agent instructions; the MCP CLI install above provides the actual tools.

## After the project is published

Once the Git remote exists, a user can install the tagged release without downloading the repo manually:

```bash
uv tool install git+https://github.com/<owner>/<repo>.git@v0.2.1
```

The harness command remains `youtube-clipper-mcp` after this install. When the package is published to PyPI, this can become `uv tool install youtube-auto-clipper`.
