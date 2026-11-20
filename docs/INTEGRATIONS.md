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

For each release, update the project version, commit the change, create the matching tag (for example, `v0.3.0`), then push the commit and tag. Publishing starts after the release tests pass. Version `0.2.3` is the first release using this workflow.

## Candidate review workflow (v0.3)

Install Kairos 0.3 or newer to use `discover_clip_candidates`. Upgrade an existing installation and restart your MCP client to refresh its tool schemas.

Ask your agent: "Find five useful teaching moments in `/absolute/path/video.mp4`, using instruction mode and offline selection. Show the timestamps, reasons, confidence, and thumbnails before rendering."

The agent should call `discover_clip_candidates` with `path`, `mode: "instruction"`, `goal: "useful teaching moments"`, `count: 5`, and `use_ai: false`. Use `gaming` for experimental commentary/reaction analysis. `auto` classifies each candidate from transcript cues; unsupported content is labeled unknown. Inspect per-candidate mismatch and boundary warnings.

After review, ask: "Render candidate_01 and candidate_03 from that plan." The agent calls `generate_clips` with the same local source, `candidate_plan` set to the returned `plan_path`, and `candidate_ids: ["candidate_01", "candidate_03"]`. The fingerprint must match the video and timestamps must be inside its duration. For an authorized YouTube URL, set `allow_download: true` explicitly. Discovery retains a local source beside the plan; use the returned local `source` for review and selected rendering.

## Long-running work with background jobs (v0.3)

Use `start_clip_job(kind="discover", options={"source": "/absolute/video.mp4", "mode": "conversation", "use_ai": false})`, then poll `get_clip_job(job_id=...)`. Completed status includes the result object and its saved path. Set `include_result=false` to avoid returning the result repeatedly. For rendering, use `kind="render"` with `source`, `candidate_plan`, and `candidate_ids` in `options`. Job output directories are assigned automatically; an `output_dir` option is overridden to protect other jobs.

Use `cancel_clip_job` to request cancellation. Wait for `cancelled`, `failed`, or `completed` before treating the job as finished. Progress is a phase estimate, not an ETA. Native inference and network calls may delay cancellation; FFmpeg children are terminated promptly at polling checkpoints. Jobs are session-scoped and cannot resume across server restarts. Synchronous tools remain available.

Transcript caching is shared by discovery, render, and transcription tools. Set `KAIROS_CACHE_DIR`, `KAIROS_DISABLE_CACHE`, or `KAIROS_JOBS_DIR` in the server's local environment if needed. Cache/result files can contain private transcript text and paths. They are local artifacts and should not be committed.

## Review studio and layouts (v0.3)

To open a plan in the local review UI, run `kairos /local/video.mp4 --review --candidate-plan /path/to/candidates.json`. Keep the terminal open. The page edits timestamps, selects IDs, and starts render jobs with progress/cancel and output links. The server binds only to 127.0.0.1 and its session URL must remain private.

Render tools and jobs accept `layout: "portrait"`, `"fit"`, or `"landscape"`. `fit` preserves the full frame with portrait padding; prefer it for gameplay, slides, and screen recordings. Portrait uses the existing `face_tracking` option. Other layouts disable face tracking. The UI's source preview does not simulate the final crop or burned captions.

## Export presets and resolution (v0.3)

`generate_clips` and render job options accept `preset: "tiktok"`, `"reels"`, or `"shorts"`, and `resolution: "auto"`, `"720p"`, or `"1080p"`. Auto selects 1080 × 1920. The 720p vertical option is 720 × 1280. Presets share the same 9:16 geometry and do not enforce all upload requirements.

Example render job options: `{"source":"/local/video.mp4","candidate_plan":"/path/candidates.json","candidate_ids":["candidate_01"],"preset":"reels","resolution":"720p","layout":"fit"}`. Use `portrait` to crop/follow faces or `fit` to preserve the full source. For custom landscape, omit the platform preset; 720p then means 1280 × 720 and 1080p means 1920 × 1080.

These options are also available as dropdowns in the local review page. The manifest's `export` object records the actual target dimensions and encoding. Upscaling does not restore detail absent from the source.

## Editorial selection in 0.3

Discovery, direct rendering, and `find_highlights` share the same selection policy. Pass `mode` and `goal` to direct rendering and render jobs when not using a reviewed plan. Reviewed IDs and edited timestamps remain authoritative.

Offline selection maps common English/Indonesian goal concepts through a small lexicon, groups ASR fragments at punctuation/pauses, penalizes repetition/CTA and content transitions, and reports `content_mode`, `classification_evidence`, `goal_matches`, `boundary`, and warnings per candidate. This is explainable heuristic matching, not arbitrary cross-language semantic comprehension. Gemini proposals are optionally used, validated, and snapped back to transcript windows; overlapping snapped proposals are deduplicated. A mode/goal unsupported by the content should not be presented as a detected event.
