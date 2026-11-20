# Kairos agent harness integrations

Kairos exposes one local MCP server over stdio. Install it once as a global CLI, then every MCP-compatible harness can launch the same command name: `kairos-mcp`. This avoids per-harness virtual-environment paths. Each harness still needs a server registration because its configuration format is different.

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

If the harness cannot resolve `kairos-mcp`, run `uv tool update-shell`, reopen the harness, and try again. Use an absolute executable path only for a harness that does not inherit the user's PATH.

## Codex

Codex CLI, its IDE extension, and the Codex desktop app share MCP configuration. With Codex CLI, add the MCP server once:

```bash
codex mcp add kairos -- \
  kairos-mcp
```

Or add this to `~/.codex/config.toml`:

```toml
[mcp_servers.kairos]
command = "kairos-mcp"
```

Then restart/reload Codex and check `/mcp` or `codex mcp list`.

## Hermes Agent

Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  kairos:
    command: "kairos-mcp"
    args: []
    timeout: 3600
```

Restart Hermes. The tools should appear under the `mcp-kairos` toolset.

## OpenClaw

Add an MCP server in Control UI → Settings → MCP, select **Stdio**, and enter `kairos-mcp` as the command. For config-file setup, add this to the OpenClaw configuration (JSON5):

```json5
{
  mcp: {
    servers: {
      kairos: {
        command: "kairos-mcp",
        args: [],
        enabled: true,
      },
    },
  },
}
```

Verify the connection with `openclaw mcp status` or `openclaw mcp doctor kairos --probe`.

## Other MCP clients

Choose **stdio/local command** as the transport and use `kairos-mcp`. The server provides `transcribe_local_video`, `find_highlights`, and `generate_clips` tools. YouTube downloads stay disabled unless the caller explicitly sets `allow_download: true`.

## Install the skill in multiple agents

The repo's `SKILL.md` follows the portable Agent Skills format. Users can install the skill into compatible agents with the Vercel Skills CLI, which detects supported agents and links one canonical skill copy:

```bash
npx skills add <owner>/<repo> --skill kairos -g
```

This installs agent instructions; the MCP CLI install above provides the actual tools.

## Install a tagged release from GitHub

Install the tagged release without downloading the repository manually:

```bash
uv tool install git+https://github.com/gempurbayu/kairos.git@v0.2.2
```

The harness command remains `kairos-mcp` after this install. When the package is published to PyPI, this can become `uv tool install kairos-video-clipper`.
