# Changelog

Notable changes to Kairos are recorded here. This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/gempurbayu/kairos/compare/v0.2.3...HEAD
[0.2.3]: https://github.com/gempurbayu/kairos/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/gempurbayu/kairos/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/gempurbayu/kairos/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/gempurbayu/kairos/releases/tag/v0.2.0
