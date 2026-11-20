<p align="center">
  <img src="https://raw.githubusercontent.com/gempurbayu/kairos/main/assets/kairos-logo.svg" alt="Kairos — Find the moment that matters" width="520">
</p>

# Kairos

**Find the moment that matters.** Kairos is a local-first tool that turns authorized long-form videos into portrait short clips. It transcribes speech, finds candidate highlights, tracks the largest visible face while reframing, and renders captioned MP4 clips with editable subtitle files.

Kairos can run from the command line or expose the same workflow as an MCP server for Codex, Hermes, OpenClaw, and other compatible agent harnesses.

## Features

- Local speech transcription with faster-whisper and word-level timestamps.
- Offline highlight scoring, with optional Gemini-assisted selection.
- Portrait 9:16 rendering with FFmpeg and optional OpenCV face tracking.
- TikTok-style karaoke captions burned into each MP4, plus an editable SRT file.
- A JSON manifest containing selected timestamps, titles, scores, and output paths.
- One shared `kairos-mcp` entry point for MCP clients, with global-install and direct-from-PyPI options.
- A portable Agent Skill in [`skills/kairos/SKILL.md`](skills/kairos/SKILL.md).

## Requirements

- Python 3.10 or newer.
- FFmpeg and ffprobe available on `PATH`. FFmpeg must include the `ass`/libass subtitle filter; check with `ffmpeg -filters | grep ass`.
- `uv` for the global MCP installation instructions below.
- Internet access to install dependencies and download Whisper model weights on first use. Gemini requests and authorized YouTube downloads also require internet access.
- Enough disk space and memory for the selected Whisper model and video rendering.

## Install

```bash
git clone https://github.com/gempurbayu/kairos.git
cd kairos
python -m venv .venv
```

Activate the virtual environment, then install Kairos:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

The `kairos` command is now available in the active virtual environment. For Gemini-assisted highlight selection, copy `.env.example` to `.env` and set `GEMINI_API_KEY`. Without a key, Kairos uses its offline transcript heuristic. Keep `.env` private; it is excluded by `.gitignore`.

## Quick start

Process a local video without using Gemini:

```bash
kairos ./path/to/video.mp4 --offline --count 3 --output ./output
```

Use Gemini-assisted selection when `GEMINI_API_KEY` is configured:

```bash
kairos ./path/to/video.mp4 --count 5 --min-duration 20 --max-duration 45
```

YouTube downloads require both the explicit `--allow-download` flag and permission to use the video:

```bash
kairos 'https://www.youtube.com/watch?v=VIDEO_ID' --allow-download --count 3
```

The first transcription run downloads the selected faster-whisper model. `base` is the default and is a practical starting point for CPU use.

### CLI options

| Option | Default | Description |
| --- | --- | --- |
| `--output PATH` | `output` | Directory for clips, subtitles, and manifest. |
| `--count N` | `3` | Maximum number of clips to create. |
| `--min-duration SECONDS` | `20` | Minimum clip duration. |
| `--max-duration SECONDS` | `60` | Maximum clip duration. |
| `--model NAME` | `base` | faster-whisper model to use, such as `base` or `small`. |
| `--offline` | off | Do not use Gemini highlight selection. |
| `--no-face-tracking` | off | Use a centered crop instead of face tracking. |
| `--allow-download` | off | Explicitly permit a YouTube download when you have the rights to use that video. |

Run `kairos --help` to see the full command help.

## Connect an agent harness

Install FFmpeg and [uv](https://docs.astral.sh/uv/getting-started/installation/), then install Kairos as an editable global uv tool:

```bash
# macOS/Linux
./scripts/setup.sh

# Windows PowerShell
.\scripts\setup.ps1
```

Every MCP-compatible harness can then launch the same command, `kairos-mcp`; no per-harness virtual-environment path is needed. Register the server once in each harness using the examples in [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md). The existing `youtube-clipper` and `youtube-clipper-mcp` command names remain available as compatibility aliases.

To skip the global installation, configure the harness to launch Kairos from PyPI with `uvx`. For example, in Codex CLI:

```bash
codex mcp add kairos -- \
  uvx --from kairos-video-clipper kairos-mcp
```

The Codex desktop config, Hermes, and OpenClaw examples are in [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md). The first `uvx` launch downloads and prepares dependencies; later launches use uv's cache. Install FFmpeg on the machine running Kairos. Direct `uvx` installs use offline highlight selection unless `GEMINI_API_KEY` is available in the server process environment. These PyPI commands work after version `0.2.3` finishes publishing.

The MCP server provides these tools:

| Tool | Purpose |
| --- | --- |
| `transcribe_local_video` | Transcribe a local video and return timestamped segments. |
| `find_highlights` | Find and rank candidate moments in a local video. |
| `generate_clips` | Render portrait clips, captions, SRT files, and a manifest. |

YouTube downloads remain disabled unless a caller explicitly sets `allow_download: true`. Confirm that the user has the rights to use the source video before enabling downloads.

### Example request in an agent chat

After connecting Kairos, ask the agent:

> Create three portrait clips from `/absolute/path/to/podcast.mp4`. Make each 20–45 seconds, use offline highlight selection and face tracking, and save the MP4s, SRT files, and manifest to `/absolute/path/to/kairos-output`. Summarize the selected timestamps when finished.

This calls `generate_clips` with arguments like:

```json
{
  "source": "/absolute/path/to/podcast.mp4",
  "output_dir": "/absolute/path/to/kairos-output",
  "count": 3,
  "min_duration": 20,
  "max_duration": 45,
  "use_ai": false,
  "face_tracking": true
}
```

### Install the Agent Skill

Install the portable skill into a supported agent with the [Vercel Skills CLI](https://skills.sh/):

```bash
npx skills add gempurbayu/kairos --skill kairos -g
```

The skill provides agent instructions; the MCP installation provides the executable tools.

## Install from PyPI

Install Kairos from PyPI:

```bash
uv tool install kairos-video-clipper
```

For a direct harness launch without a Git URL, configure the MCP command as `uvx` with arguments `--from`, `kairos-video-clipper`, and `kairos-mcp`. The first launch downloads the package and dependencies; subsequent launches use uv's cache.

## Preview and select candidates (v0.3 development)

The working tree adds a discovery workflow; the latest published package may not include it yet. Install this checkout with `pip install -e .` to use it.

```bash
kairos ./video.mp4 --discover --mode instruction --goal "useful tips" --offline --count 5 --output ./candidates
kairos ./game.mp4 --discover --mode gaming --goal "clutch funny reactions" --offline --output ./candidates
```

Discovery writes a new review folder containing `candidates.json` and up to three JPEG thumbnails per candidate. Review the returned `plan_path`, IDs, transcript excerpts, and reasons, then render only your chosen IDs:

```bash
kairos ./video.mp4 --candidate-plan ./candidates/review-EXAMPLE/candidates.json --select candidate_01 candidate_03 --output ./output/reviewed
```

Replace `review-EXAMPLE` with the actual review folder. A SHA-256 fingerprint checks that the plan targets the same video. Rendering re-transcribes the video to produce captions; transcript caching and background jobs are not implemented yet.

Modes are `auto`, `conversation`, `instruction`, and experimental `gaming`. Auto mode uses transcript keywords and can be overridden. Offline scoring recognizes English and some Indonesian cues. Use `--goal` to favor matching transcript terms; optional Gemini selection also receives the mode and goal. Candidate scores include hook, context, pacing, goal relevance, audio dynamics, and sampled frame changes. Confidence labels are heuristic, not calibrated probabilities. Audio/frame signals are sampled only for the transcript shortlist, so silent action footage is not supported. Gaming does not recognize specific events or HUD information. Use `--no-media-analysis` to skip audio/frame sampling.

For MCP, call `discover_clip_candidates`, review the response, and pass `plan_path` as `candidate_plan` plus the chosen `candidate_ids` to `generate_clips`. Existing `find_highlights` and direct rendering remain available.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | unset | Enables Gemini-assisted highlight selection. Without it, offline scoring is used. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model for highlight selection. |
| `WHISPER_MODEL` | `base` | Default local transcription model; `--model` overrides it for a CLI run. |

Variables can be placed in a local `.env` file or supplied by the process environment. Never commit real credentials.

## Output files

Each run writes files into the selected output directory:

```text
output/
├── clip_01.mp4
├── clip_01.srt
├── clip_02.mp4
├── clip_02.srt
└── manifest.json
```

Captions are burned into the MP4 in short word groups with karaoke highlighting. SRT files remain editable in video-editing software. The manifest records clip timestamps, titles, scores, selection method, face-tracking setting, and output paths. Existing files with the same names are overwritten, so choose a different output directory to retain previous results.

## How it works and known limitations

- faster-whisper transcribes audio locally and supplies word timestamps.
- Offline selection scores transcript windows using speech pacing, vocabulary variety, hook words, and sentence completion. Gemini can rank candidate moments when configured; failures fall back to offline selection.
- Face tracking samples frames and follows the largest detected face. If no face is found, Kairos uses a centered crop. It does not identify or follow a particular person.
- Highlight selection is based on transcript signals; it is not visual scene understanding and cannot guarantee virality or editorial quality.
- Videos with little or no speech may produce fewer clips or no clips.
- Kairos does not bypass DRM, access restrictions, or platform safeguards. Follow applicable copyright rules and platform terms when processing or downloading videos.

## Development

```bash
python -m pip install -e . pytest
python -m pytest -q
```

GitHub Actions runs the test suite on Python 3.10, 3.11, and 3.12 for pushes and pull requests. Before changing behavior, review [`AGENTS.md`](AGENTS.md) for repository conventions and safety requirements. Keep user media, generated outputs, API keys, and local `.env` files out of commits.

## Release and PyPI publishing

See [`CHANGELOG.md`](CHANGELOG.md) for release history. Pushing a version tag such as `v0.2.4` runs tests, builds the distributions, checks that the tag matches `pyproject.toml`, and publishes them to PyPI through GitHub Actions. The publisher uses PyPI Trusted Publishing (OIDC), so no PyPI API token is stored in GitHub.

Version `0.2.3` was the first automatic publication. The [PyPI Trusted Publisher](https://docs.pypi.org/trusted-publishers/) is configured for owner `gempurbayu`, repository `kairos`, workflow `publish.yml`, and environment `pypi`. Every release tag must match the package version exactly.

## License

Kairos is licensed under the [MIT License](LICENSE). Copyright (c) 2026 Gempur Bayu. Third-party dependencies, models, and source videos remain subject to their own licenses and terms.
