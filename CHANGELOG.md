# Changelog

Notable changes to Kairos are recorded here. This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- TikTok/Reels/Shorts vertical export presets and auto/720p/1080p output choices across CLI, MCP, jobs, and review UI.
- Export settings in output manifests and explicit H.264/yuv420p output encoding.

- Local browser review studio with candidate playback, timestamp edits, selection, render progress/cancel, and MP4/SRT links.
- Full-frame portrait padding and landscape layout presets alongside face-tracked portrait cropping.
- Explicitly authorized YouTube discovery downloads retained alongside their review plan.

- Content-addressed local transcript caching shared across discovery and rendering, with model/configuration invalidation and atomic writes.
- Session-scoped MCP background jobs with a bounded queue, phase progress, cancellation, isolated outputs, and persisted result files.
- Synthetic FFmpeg/MCP integration tests and an interval-based candidate evaluation script for human-marked video moments.

- Reviewable local candidate discovery with conversation, instruction, auto, and experimental commented-gaming modes.
- Editorial goals, component scores, heuristic confidence, transcript excerpts, audio dynamics, sampled frame changes, and thumbnail previews.
- CLI discovery and candidate selection, plus the `discover_clip_candidates` MCP tool.
- Video fingerprint and timestamp validation before rendering selected candidate IDs.

### Fixed

- Review streaming now handles browser-abandoned video ranges without noisy connection errors.

- Constrained the MCP SDK to its compatible v1 API; v2 removes the FastMCP import used by this server.

- Pipeline fallback warnings now go to stderr to preserve MCP stdio output.
- Rejected non-finite duration options and AI timestamps outside transcript coverage.

## [0.2.4] - 2026-11-21

### Added

- MIT License with copyright attributed to Gempur Bayu.
- License metadata and the license file in Python package distributions.
- Release history in `CHANGELOG.md` and contributor rules for keeping it updated.

## [0.2.3] - 2026-11-21

### Added

- Automated PyPI publishing from version tags using GitHub Actions and PyPI Trusted Publishing.
- Direct harness installation examples for Codex, Hermes, and OpenClaw using the published package.
- An expanded English README with CLI and agent usage examples.

### Changed

- Published the distribution as `kairos-video-clipper` so it can be installed by package name.
- Updated harness examples to use `kairos-mcp` from PyPI.

## [0.2.2] - 2026-11-21

### Added

- Kairos branding and a minimal SVG logo.
- Contributor guidance in `AGENTS.md`.
- A portable Agent Skill published as `kairos`.

### Changed

- Renamed the product and MCP server identity to Kairos.
- Added `kairos` and `kairos-mcp` commands while keeping the previous command names as aliases.

## [0.2.1] - 2026-11-21

### Added

- A globally installed MCP command that can be shared across compatible agent harnesses.
- Setup scripts and integration instructions for Codex, Hermes, OpenClaw, and other MCP clients.

## [0.2.0] - 2026-11-21

### Added

- Local video transcription with faster-whisper and optional Gemini-assisted highlight selection.
- Offline highlight scoring, portrait clip rendering, face tracking, karaoke captions, SRT subtitles, and a JSON manifest.
- CLI and MCP server entry points, a portable Agent Skill, and initial GitHub Actions CI.

[Unreleased]: https://github.com/gempurbayu/kairos/compare/v0.2.4...HEAD
[0.2.4]: https://github.com/gempurbayu/kairos/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/gempurbayu/kairos/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/gempurbayu/kairos/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/gempurbayu/kairos/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/gempurbayu/kairos/releases/tag/v0.2.0
