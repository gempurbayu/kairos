# Kairos contributor instructions

These instructions apply to the whole repository. Follow them for bug fixes, refactors, documentation changes, and new features.

## Project identity and compatibility

- Use **Kairos** as the product name in user-facing docs and agent configuration examples.
- The supported command names are `kairos` and `kairos-mcp`. Keep the legacy `youtube-clipper` and `youtube-clipper-mcp` entry points working unless a deliberate breaking change is approved and documented.
- The current Python import package is `youtube_auto_clipper`. Avoid renaming it as part of unrelated work; existing code and integrations may import it.
- Keep one canonical MCP server command so clients do not need project-specific executable paths. Update [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) when integration behavior changes.
- Keep repository documentation and user-facing messages in English.

## Architecture

- Python source lives in `src/youtube_auto_clipper/` and command-line entry points are declared in `pyproject.toml`.
- `pipeline.py` owns transcription, highlight selection, cropping, caption generation, and rendering. Keep the CLI and MCP server as thin interfaces over the shared pipeline.
- Preserve local/offline processing when adding optional AI services. A missing API key or remote-service failure must not make the basic local workflow unusable.
- Keep generated MP4, SRT, and manifest outputs compatible unless a change explicitly updates and documents the output contract.
- Add dependencies only when the feature needs them; document external requirements such as FFmpeg and ffprobe.

## Video rights and security

- Process only videos the user owns or is authorized to use. YouTube downloading must remain opt-in through `--allow-download` or the MCP argument `allow_download: true`.
- Do not bypass DRM, access restrictions, or platform safeguards. Do not describe highlight scores as a guarantee of virality.
- Treat transcripts, model responses, paths, and downloaded media as untrusted input. Validate model-generated clip ranges before rendering.
- Never commit API keys, access tokens, private keys, user media, generated output, or local environment files. `.env` and output directories should remain ignored; `.env.example` may contain empty credential placeholders and non-secret defaults only.

## Changes and documentation

- Keep changes focused and follow the existing Python and Markdown style.
- Add or update focused pytest coverage for behavior changes, including error paths where practical.
- Update the README, MCP integration guide, and Agent Skill when commands, configuration, tool arguments, defaults, or output files change.
- Keep examples copyable, safe by default, and consistent with the actual CLI and MCP schemas.
- Do not silently change public command names, MCP tool names, configuration keys, or output formats.

## Verification

- Install the project and test dependency with `python -m pip install -e . pytest`.
- Run the suite with `python -m pytest -q` after code changes.
- GitHub Actions is the compatibility check for Python 3.10, 3.11, and 3.12.
- For packaging changes, confirm the declared entry points and setup scripts agree. For integration changes, check every affected example in `docs/INTEGRATIONS.md`.
- The PyPI workflow publishes only pushed `v*` tags after tests pass and only when the tag exactly matches `project.version` in `pyproject.toml`. Do not add API tokens to the workflow; publishing uses PyPI Trusted Publishing.

## Collaboration

- Use clear, focused commit messages and explain user-visible behavior changes in the pull request.
- Do not commit, push, publish releases, or change repository visibility unless the repository owner requests it.
- Call out limitations, migration steps, and any change that requires users to reinstall Kairos or update harness configuration.
