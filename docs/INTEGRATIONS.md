# Kairos agent harness integrations

Kairos exposes one local MCP server over stdio. You can install it once as a global CLI and use `kairos-mcp` in every harness, or let a harness launch the pinned GitHub release with `uvx` on first use. Both approaches avoid per-harness virtual-environment paths. Each harness still needs a server registration because its configuration format is different.

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

## Install directly from a harness

These examples use `uvx` to fetch Kairos from PyPI and create its tool environment on first launch. They work once version `0.2.3` finishes publishing. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first, and make sure `uvx` is on `PATH`. The first launch needs internet access and may take longer while Python dependencies are installed; later launches use uv's cache. FFmpeg must also be installed on the machine running the server.

Without `GEMINI_API_KEY` in the server process environment, Kairos still works and selects highlights offline. To use Gemini with a direct `uvx` configuration, pass the key through the harness's local MCP environment settings. Do not put real keys in repository files.

### Codex

With Codex CLI, run:

```bash
codex mcp add kairos -- \
  uvx --from kairos-video-clipper kairos-mcp
```

Or add this to `~/.codex/config.toml`:

```toml
[mcp_servers.kairos]
command = "uvx"
args = [
  "--from",
  "kairos-video-clipper",
  "kairos-mcp",
]
```

Reload Codex and check `/mcp` or `codex mcp list`.

### Hermes Agent

Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  kairos:
    command: "uvx"
    args:
      - "--from"
      - "kairos-video-clipper"
      - "kairos-mcp"
    timeout: 3600
```

Restart Hermes. The tools should appear under the `mcp-kairos` toolset.

### OpenClaw

In Control UI → Settings → MCP, add a **Stdio** server with command `uvx` and arguments:

```text
--from kairos-video-clipper kairos-mcp
```

For JSON5 configuration, use:

```json5
{
  mcp: {
    servers: {
      kairos: {
        command: "uvx",
        args: [
          "--from",
          "kairos-video-clipper",
          "kairos-mcp",
        ],
        enabled: true,
      },
    },
  },
}
```

Check the connection with `openclaw mcp status` or `openclaw mcp doctor kairos --probe`.

## Install once, then connect

For a reusable global installation, install the pinned release once:

```bash
uv tool install kairos-video-clipper
```

Then use the shorter `kairos-mcp` command in each harness configuration. This avoids resolving and preparing the package on each harness's first launch.

For direct harness launch from PyPI, set command `uvx` with arguments `--from`, `kairos-video-clipper`, and `kairos-mcp`.

For example, Codex CLI can use:

```bash
codex mcp add kairos -- uvx --from kairos-video-clipper kairos-mcp
```

In Codex config, set `command = "uvx"` and `args = ["--from", "kairos-video-clipper", "kairos-mcp"]`. Use the same command and argument list in Hermes and OpenClaw after the package's first PyPI release.

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

Choose **stdio/local command** as the transport and use `kairos-mcp` after installing Kairos globally. For a direct launch, use command `uvx` with arguments `--from`, `kairos-video-clipper`, and `kairos-mcp`. The server provides `transcribe_local_video`, `find_highlights`, and `generate_clips` tools. YouTube downloads stay disabled unless the caller explicitly sets `allow_download: true`.

## Install the skill in multiple agents

The repo's `SKILL.md` follows the portable Agent Skills format. Users can install the skill into compatible agents with the Vercel Skills CLI, which detects supported agents and links one canonical skill copy:

```bash
npx skills add gempurbayu/kairos --skill kairos -g
```

This installs agent instructions; the MCP CLI install above provides the actual tools.

The harness command remains `kairos-mcp` after this install.

## Automatic PyPI publishing

The [publish workflow](../.github/workflows/publish.yml) runs when a `v*` tag is pushed. It tests Python 3.10–3.12, verifies that the tag equals the version in `pyproject.toml`, builds the wheel and source archive, then publishes through PyPI Trusted Publishing. No PyPI token is stored in repository secrets.

For the first publication, configure a [pending publisher in PyPI](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) with:

- Owner: `gempurbayu`
- Repository: `kairos`
- Workflow: `publish.yml`
- GitHub environment: `pypi`

For each release, update the project version, commit the change, create the matching tag (for example, `v0.2.4`), then push the commit and tag. Publishing starts after the release tests pass. Version `0.2.3` is the first release using this workflow.
