# YouTube Auto Clipper v0.2 — Hybrid AI Skill + MCP

An executable Python tool that turns authorized long-form videos into 9:16 short clips. Local **faster-whisper** transcribes with word timestamps, optional **Gemini** ranks highlights, and **FFmpeg** renders MP4 with TikTok-style karaoke captions burned in plus a separate SRT. OpenCV face detection follows the largest visible face while cropping. An **MCP server** exposes tools to AI agents; a portable **SKILL.md** documents the workflow.

## Requirements
- Python 3.10+
- FFmpeg + ffprobe on PATH (`ffmpeg -version`)
- Internet for installing dependencies, Gemini requests, or authorized YouTube downloads
- Enough RAM/disk for faster-whisper and video rendering
- FFmpeg built with the `ass`/libass subtitle filter (check with `ffmpeg -filters | grep ass`)

## Install
```bash
git clone <YOUR_REPO_URL>
cd youtube-auto-clipper
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
cp .env.example .env  # on Windows, copy manually
```

Set `GEMINI_API_KEY` in `.env` for AI selection. Without a key, the MVP works offline using a basic speech-density heuristic. `WHISPER_MODEL=base` is the CPU-friendly default; the first run downloads Whisper model weights.

## CLI examples
```bash
# Fully local processing of a video file
youtube-clipper ./examples/input.mp4 --offline --count 3 --output ./output

# Disable face tracking and retain a centered portrait crop
youtube-clipper ./examples/input.mp4 --offline --no-face-tracking

# Gemini-assisted highlight selection
youtube-clipper ./examples/input.mp4 --count 5 --min-duration 20 --max-duration 45

# Only if you have rights to download and process this YouTube video:
youtube-clipper 'https://www.youtube.com/watch?v=YOUR_VIDEO_ID' --allow-download --count 3
```

## Connect an agent harness
Install `uv` and FFmpeg, then run `./scripts/setup.sh` (Windows: `scripts/setup.ps1`) once. The server is installed as a global command, so each harness uses the same `youtube-clipper-mcp` command over **stdio** without a project-specific executable path. Copy-ready Codex, Hermes, OpenClaw, and generic MCP examples are in [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md). The portable agent instructions are in `skills/youtube-clipper/SKILL.md`.

## Output
```
output/
  clip_01.mp4
  clip_01.srt
  clip_02.mp4
  clip_02.srt
  manifest.json
```
Captions are burned into MP4 in short word groups with karaoke highlighting; `.srt` is also included for editing. `manifest.json` contains timestamps, titles, scores, selection method, tracking setting, and paths. Face tracking follows the largest face detected in samples taken every two seconds; when no face is found, it uses a centered crop. The heuristic cannot guarantee perfect framing and does not identify a specific person.

## Limitations / roadmap
- Highlight scoring uses transcript pacing, vocabulary variety, hook words, and sentence completion; it is not visual scene understanding and does not guarantee performance.
- Gemini API failure falls back to offline selection.
- A video without enough spoken content may yield fewer clips or none.
- `--allow-download` is an explicit user authorization flag, not a license check. You must follow applicable copyright and YouTube terms.
- Existing output names are overwritten. Use a new output directory for each job.
- Future: shot-aware reframing, deduplication, batch jobs, dashboard, publishing integration.

## Tests
```bash
pip install pytest
pytest -q
```
