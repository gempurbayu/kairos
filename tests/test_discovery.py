import json
import math
from pathlib import Path

import pytest

from youtube_auto_clipper import discovery, pipeline


SEGMENTS = [
    {"start": 0, "end": 12, "text": "Here is a tutorial on how to fix this error."},
    {"start": 12, "end": 25, "text": "First use this step and check the result."},
    {"start": 25, "end": 40, "text": "We won the boss fight, gg, what a clutch!"},
    {"start": 40, "end": 50, "text": "That was a great win!"},
]


@pytest.mark.parametrize("minimum,maximum", [(math.nan, 60), (20, math.inf), (0, 60), (40, 20)])
def test_reject_bad_durations(minimum, maximum):
    with pytest.raises(ValueError):
        discovery.validate_options(3, minimum, maximum, "auto")


def test_category_and_goal_affect_ranking():
    assert discovery.choose_mode(SEGMENTS[:2], "auto") == "instruction"
    assert discovery.choose_mode([], "gaming") == "gaming"
    clips = discovery.rank_candidates(SEGMENTS, 1, 20, 30, "gaming", "clutch boss")
    assert clips[0]["start"] == 25
    assert clips[0]["scores"]["goal_relevance"] == 100
    assert "clutch" in clips[0]["reason"]


def test_discovery_preview_and_selection(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fixture video")
    monkeypatch.setattr(discovery, "transcribe", lambda *_: (SEGMENTS, "en"))
    result = discovery.discover_candidates(str(video), str(tmp_path / "previews"),
                                           count=2, min_duration=20, max_duration=30,
                                           mode="gaming", analyze_media=False)
    assert result["clips"]
    assert result["clips"][0]["confidence"] == "low"
    assert result["clips"][0]["scores"]["visual_change"] is None
    key = result["clips"][0]["id"]
    selected = discovery.load_selection(result["plan_path"], video, [key])
    assert selected[0]["id"] == key
    with pytest.raises(ValueError, match="Unknown"):
        discovery.load_selection(result["plan_path"], video, ["missing"])
    with pytest.raises(ValueError, match="unique"):
        discovery.load_selection(result["plan_path"], video, [key, key])
    video.write_bytes(b"changed video")
    with pytest.raises(ValueError, match="match"):
        discovery.load_selection(result["plan_path"], video, [key])


def test_render_uses_only_reviewed_candidates(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fixture video")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"schema_version": 1, "source_sha256": discovery.fingerprint(video),
                               "clips": [{"id": "chosen", "start": 2, "end": 22}]}))
    monkeypatch.setattr(pipeline, "require_binary", lambda *_: None)
    monkeypatch.setattr(pipeline, "run_command", lambda *_: '{"format":{"duration":"50"}}')
    monkeypatch.setattr(pipeline, "transcribe", lambda *_: (SEGMENTS, "en"))
    rendered = []
    monkeypatch.setattr(pipeline, "render_clip", lambda video, start, end, *args, **kwargs: rendered.append((start, end)))
    result = pipeline.process(str(video), str(tmp_path / "out"), candidate_plan=str(plan), candidate_ids=["chosen"])
    assert rendered == [(2, 22)]
    assert result["selection_method"] == "reviewed-candidates"
    plan.write_text(plan.read_text().replace('"end": 22', '"end": 999'))
    with pytest.raises(ValueError, match="timestamps"):
        pipeline.process(str(video), str(tmp_path / "out"), candidate_plan=str(plan), candidate_ids=["chosen"])


def test_ai_failure_keeps_offline_preview(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fixture")
    monkeypatch.setattr(discovery, "transcribe", lambda *_: (SEGMENTS, "en"))
    def fail(*args):
        raise RuntimeError("remote unavailable")
    monkeypatch.setattr(discovery, "ai_highlights", fail)
    result = discovery.discover_candidates(str(video), str(tmp_path / "review"),
                                           min_duration=20, max_duration=30,
                                           use_ai=True, analyze_media=False)
    assert result["method"] == "offline-fallback"
    assert result["clips"]
    assert result["warnings"]


def test_empty_speech_has_explicit_warning(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fixture")
    monkeypatch.setattr(discovery, "transcribe", lambda *_: ([], "en"))
    result = discovery.discover_candidates(str(video), str(tmp_path / "review"), analyze_media=False)
    assert result["clips"] == []
    assert "No speech" in result["warnings"][0]


def test_mcp_stdout_remains_clean_on_fallback(tmp_path, monkeypatch, capsys):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fixture")
    monkeypatch.setattr(pipeline, "require_binary", lambda *_: None)
    monkeypatch.setattr(pipeline, "transcribe", lambda *_: (SEGMENTS, "en"))
    monkeypatch.setattr(pipeline, "render_clip", lambda *args, **kwargs: None)
    def fail(*args):
        raise RuntimeError("remote error with sensitive context")
    monkeypatch.setattr(pipeline, "ai_highlights", fail)
    pipeline.process(str(video), str(tmp_path / "output"))
    output = capsys.readouterr()
    assert output.out == ""
    assert "offline" in output.err
    assert "sensitive" not in output.err


def test_discovery_download_remains_opt_in(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="explicitly allow"):
        discovery.discover_candidates('https://www.youtube.com/watch?v=example', str(tmp_path))
    def download(source, workspace, allow_download):
        assert allow_download is True
        video = workspace / 'source.mp4'
        video.write_bytes(b'authorized source fixture')
        return video
    monkeypatch.setattr(discovery, 'get_source', download)
    monkeypatch.setattr(discovery, 'transcribe', lambda *_: (SEGMENTS, 'en'))
    result = discovery.discover_candidates('https://www.youtube.com/watch?v=example', str(tmp_path),
                                           analyze_media=False, allow_download=True)
    assert Path(result['source']).is_file()
    assert Path(result['source']).is_relative_to(Path(result['plan_path']).parent)
