"""Synthetic media/protocol checks; not evidence of real-world highlight quality."""
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from youtube_auto_clipper import discovery, pipeline




def has_ass():
    return " ass " in subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout


def test_discover_select_render_with_cached_transcript(video, tmp_path, monkeypatch):
    if not has_ass():
        pytest.skip("This FFmpeg build lacks libass; caption integration runs in CI")
    monkeypatch.setenv("KAIROS_CACHE_DIR", str(tmp_path / "cache"))
    calls = []
    def transcribe(*_):
        calls.append(1)
        return [{"start": 0., "end": 2., "text": "Here is a useful tutorial tip."}], "en"
    monkeypatch.setattr(pipeline, "_transcribe_uncached", transcribe)
    preview = discovery.discover_candidates(str(video), str(tmp_path / "previews"),
                                            count=1, min_duration=1, max_duration=3, mode="instruction")
    assert len(preview["clips"][0]["thumbnails"]) == 3
    result = pipeline.process(str(video), str(tmp_path / "rendered"),
                              candidate_plan=preview["plan_path"], candidate_ids=["candidate_01"],
                              face_tracking=False)
    assert calls == [1], "Review to render should reuse the cached transcript"
    clip = result["clips"][0]
    assert Path(clip["video"]).stat().st_size > 0
    assert "tutorial" in Path(clip["subtitles"]).read_text()
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-of", "json", clip["video"]]))
    stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    assert (stream["width"], stream["height"]) == (1080, 1920)


def test_mcp_stdio_job_workflow(video, tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
               KAIROS_CACHE_DIR=str(tmp_path / "cache"), KAIROS_JOBS_DIR=str(tmp_path / "jobs"))
    # Replace only inference; transport, queue, cache, media sampling and rendering are real.
    script = '''
from youtube_auto_clipper import pipeline
pipeline._transcribe_uncached = lambda *_: ([{"start":0.,"end":2.,"text":"A useful tutorial tip."}], "en")
from youtube_auto_clipper.mcp_server import main
main()
'''
    async def run():
        params = StdioServerParameters(command=sys.executable, args=["-c", script], env=env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                async def call(name, args):
                    result = await session.call_tool(name, args)
                    assert not result.isError, result
                    return json.loads(result.content[0].text)
                async def finish(key):
                    for _ in range(300):
                        status = await call("get_clip_job", {"job_id": key})
                        if status["status"] in ("completed", "cancelled", "failed"):
                            assert status["status"] == "completed", status
                            assert status["result"] == json.loads(Path(status["result_path"]).read_text())
                            return status["result"]
                        await asyncio.sleep(.1)
                    raise AssertionError("Job timed out")
                job = await call("start_clip_job", {"kind": "discover", "options": {
                    "source": str(video), "count": 1, "min_duration": 1, "max_duration": 3,
                    "mode": "instruction"}})
                plan = await finish(job["id"])
                assert plan["clips"][0]["id"] == "candidate_01"
                if has_ass():
                    job = await call("start_clip_job", {"kind": "render", "options": {
                        "source": str(video), "candidate_plan": plan["plan_path"],
                        "candidate_ids": ["candidate_01"], "face_tracking": False}})
                    rendered = await finish(job["id"])
                    assert Path(rendered["clips"][0]["video"]).is_file()
    asyncio.run(run())
