"""MCP stdio entry point shared by Codex, Hermes, OpenClaw, and other clients."""
import json
import threading
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .discovery import discover_candidates, validate_options
from .pipeline import ai_highlights, fallback_highlights, process, transcribe


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
                    max_duration: float = 60, use_ai: bool = True) -> str:
    """Suggest non-overlapping short highlights from a local video's transcript."""
    validate_options(count, min_duration, max_duration, "conversation")
    video = Path(path).expanduser().resolve()
    if not video.is_file():
        raise ValueError("Local video file does not exist")
    segments, language = transcribe(video)
    if use_ai:
        try:
            clips, method = ai_highlights(segments, count, min_duration, max_duration)
        except Exception:
            clips = fallback_highlights(segments, count, min_duration, max_duration)
            method = "offline-fallback"
    else:
        clips = fallback_highlights(segments, count, min_duration, max_duration)
        method = "offline"
    return json.dumps({"language": language, "method": method, "clips": clips}, ensure_ascii=False)


@mcp.tool()
def discover_clip_candidates(path: str, output_dir: str = "candidates", count: int = 5,
                             min_duration: float = 20, max_duration: float = 60,
                             mode: str = "auto", goal: str = "", use_ai: bool = False,
                             analyze_media: bool = True) -> str:
    """Preview category-aware candidates, scores, transcript excerpts, and thumbnails.

    Local videos only. Review candidates before passing plan_path and IDs to generate_clips.
    Gaming is experimental and does not recognize specific game events.
    """
    return json.dumps(discover_candidates(path, output_dir, count, min_duration,
                                         max_duration, mode, goal, use_ai,
                                         analyze_media=analyze_media), ensure_ascii=False)


@mcp.tool()
def generate_clips(source: str, output_dir: str = "output", count: int = 3,
                   min_duration: float = 20, max_duration: float = 60,
                   allow_download: bool = False, use_ai: bool = True,
                   face_tracking: bool = True, candidate_plan: str | None = None,
                   candidate_ids: list[str] | None = None) -> str:
    """Create portrait MP4 clips with burned-in captions, separate SRT files, and a manifest.

    For YouTube sources, allow_download must be true and the user must have rights to use the video.
    """
    return json.dumps(process(source, output_dir, count, min_duration,
                              max_duration, allow_download, use_ai=use_ai,
                              face_tracking=face_tracking, candidate_plan=candidate_plan,
                              candidate_ids=candidate_ids), ensure_ascii=False)


def main():
    """Run this MCP server over stdio for a local agent harness."""
    try:
        mcp.run(transport="stdio")
    finally:
        if _job_manager is not None:
            _job_manager.close()


if __name__ == "__main__":
    main()
