---
name: kairos
description: Turn authorized long-form videos into portrait clips with face tracking and TikTok-style captions using local Whisper, Gemini highlight analysis, and FFmpeg via MCP.
---

# Kairos

Use this skill when asked to identify and render highlights from long-form videos.

## Safety and rights
- Process only videos the user owns or is licensed/authorized to use.
- For YouTube URLs, ask the user to confirm authorization before setting `allow_download=true`.
- Do not bypass access restrictions, DRM, or platform safeguards.
- Never imply an offline heuristic guarantees viral performance.

## Workflow
1. Confirm source path or authorized YouTube URL, desired count and duration.
2. For a local source, prefer `discover_clip_candidates` when available. Choose `conversation` for discussions, `instruction` for teaching/demos, or experimental `gaming` for commented gameplay; use `auto` when uncertain. Pass the user's editorial goal. Show candidate IDs, timestamps, transcript excerpts, reasons, confidence, and thumbnail paths before rendering. Never claim gaming event recognition or calibrated confidence. For older installations, use `transcribe_local_video` or `find_highlights`.
3. After the user chooses candidates, pass the returned `plan_path` as `candidate_plan` and the selected IDs as `candidate_ids` to `generate_clips`. Use the same local source. If no suitable speech windows are found, explain that this workflow currently needs speech; do not invent visual highlights.
4. Call `generate_clips` with the chosen settings.
5. Read the returned manifest and report exact output paths, titles and timestamps.
6. Explain that TikTok-style captions are burned into MP4 and an editable `.srt` is also provided.

## Defaults
- 3 clips, 20–60 seconds, 1080×1920 MP4, burned-in TikTok-style captions, and separate SRT files.
- Gemini when `GEMINI_API_KEY` is set; otherwise offline speech-density heuristic.
- OpenCV samples face locations and follows the largest detected face; centered crop is used if no face is detected.

## Example MCP invocation
Tool: `generate_clips`
Arguments: `{"source":"/absolute/path/to/podcast.mp4","output_dir":"/absolute/path/to/output","count":3,"min_duration":20,"max_duration":60,"use_ai":true,"face_tracking":true}`
