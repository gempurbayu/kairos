"""MCP stdio entry point shared by Codex, Hermes, OpenClaw, and other clients."""
import json
import threading
from typing import Literal
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .discovery import discover_candidates, validate_options, select_editorial_highlights
from .pipeline import process, transcribe


mcp = FastMCP("kairos")
_job_manager = None
_job_lock = threading.Lock()


def job_manager():
    global _job_manager
    with _job_lock:
        if _job_manager is None:
            from .jobs import JobManager
            _job_manager = JobManager()
    return _job_manager


@mcp.tool()
def start_clip_job(kind: str, options: dict) -> str:
    """Start a background discover or render job; returns a job ID immediately.

    Options use the shared Python pipeline names: discover requires source; render
    requires source and optionally candidate_plan/candidate_ids. Output is isolated
    per job. Use get_clip_job and cancel_clip_job in this same server session.
    """
    return json.dumps(job_manager().submit(kind, options), ensure_ascii=False)


@mcp.tool()
def get_clip_job(job_id: str, include_result: bool = True) -> str:
    """Return queued/running/completed/failed/cancelled status and phase progress.

    Progress is an estimate by phase, not an ETA. Completed jobs include result_path.
    """
    status = job_manager().status(job_id)
    if include_result and status["status"] == "completed":
        status["result"] = json.loads(Path(status["result_path"]).read_text(encoding="utf-8"))
    return json.dumps(status, ensure_ascii=False)


@mcp.tool()
def cancel_clip_job(job_id: str) -> str:
    """Request cooperative cancellation; poll status until cancelled or completed.

    FFmpeg is terminated promptly. Model loading, inference and network calls may
    finish their current operation before cancellation is observed.
    """
    return json.dumps(job_manager().cancel(job_id), ensure_ascii=False)


@mcp.tool()
def transcribe_local_video(path: str, model: str = "base") -> str:
    """Transcribe a local video and return timestamped transcript segments as JSON."""
    video = Path(path).expanduser().resolve()
    if not video.is_file():
        raise ValueError("Local video file does not exist")
    segments, language = transcribe(video, model)
    return json.dumps({"language": language, "segments": segments}, ensure_ascii=False)


@mcp.tool()
def find_highlights(path: str, count: int = 3, min_duration: float = 20,
                    max_duration: float = 60, use_ai: bool = True,
                    mode: str = "auto", goal: str = "") -> str:
    """Suggest non-overlapping short highlights from a local video's transcript."""
    validate_options(count, min_duration, max_duration, mode)
    video = Path(path).expanduser().resolve()
    if not video.is_file():
        raise ValueError("Local video file does not exist")
    segments, language = transcribe(video)
    clips, method, warnings = select_editorial_highlights(segments, count, min_duration,
                                                         max_duration, mode, goal, use_ai)
    return json.dumps({"language": language, "method": method, "clips": clips,
                       "warnings": warnings}, ensure_ascii=False)


@mcp.tool()
def discover_clip_candidates(path: str, output_dir: str = "candidates", count: int = 5,
                             min_duration: float = 20, max_duration: float = 60,
                             mode: str = "auto", goal: str = "", use_ai: bool = False,
                             analyze_media: bool = True, allow_download: bool = False) -> str:
    """Preview category-aware candidates, scores, transcript excerpts, and thumbnails.

    YouTube URLs require allow_download and user authorization; the downloaded source
    is retained beside the review plan. Review candidates before rendering.
    Gaming is experimental and does not recognize specific game events.
    """
    return json.dumps(discover_candidates(path, output_dir, count, min_duration,
                                         max_duration, mode, goal, use_ai,
                                         analyze_media=analyze_media, allow_download=allow_download), ensure_ascii=False)


@mcp.tool()
def generate_clips(source: str, output_dir: str = "output", count: int = 3,
                   min_duration: float = 20, max_duration: float = 60,
                   allow_download: bool = False, use_ai: bool = True,
                   face_tracking: bool = True, candidate_plan: str | None = None,
                   candidate_ids: list[str] | None = None, layout: str = "portrait",
                   resolution: Literal["auto", "720p", "1080p"] = "1080p",
                   preset: Literal["tiktok", "reels", "shorts"] | None = None,
                   mode: str = "auto", goal: str = "") -> str:
    """Create portrait MP4 clips with burned-in captions, separate SRT files, and a manifest.

    Platform presets target vertical 9:16; resolution auto uses 1080p.
    For YouTube sources, allow_download must be true and the user must have rights to use the video.
    """
    return json.dumps(process(source, output_dir, count, min_duration,
                              max_duration, allow_download, use_ai=use_ai,
                              face_tracking=face_tracking, candidate_plan=candidate_plan,
                              candidate_ids=candidate_ids, layout=layout,
                              resolution=resolution, preset=preset, mode=mode, goal=goal), ensure_ascii=False)


def main():
    """Run this MCP server over stdio for a local agent harness."""
    try:
        mcp.run(transport="stdio")
    finally:
        if _job_manager is not None:
            _job_manager.close()


if __name__ == "__main__":
    main()
