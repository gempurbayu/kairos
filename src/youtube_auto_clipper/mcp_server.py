"""MCP stdio entry point shared by Codex, Hermes, OpenClaw, and other clients."""
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .pipeline import ai_highlights, fallback_highlights, process, transcribe


mcp = FastMCP("kairos")


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
def generate_clips(source: str, output_dir: str = "output", count: int = 3,
                   min_duration: float = 20, max_duration: float = 60,
                   allow_download: bool = False, use_ai: bool = True,
                   face_tracking: bool = True) -> str:
    """Create portrait MP4 clips with burned-in captions, separate SRT files, and a manifest.

    For YouTube sources, allow_download must be true and the user must have rights to use the video.
    """
    return json.dumps(process(source, output_dir, count, min_duration,
                              max_duration, allow_download, use_ai=use_ai,
                              face_tracking=face_tracking), ensure_ascii=False)


def main():
    """Run this MCP server over stdio for a local agent harness."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
