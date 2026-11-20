import json
import sys
import threading
import time

import pytest

from youtube_auto_clipper.cache import cached_transcript
from youtube_auto_clipper.jobs import JobManager
from youtube_auto_clipper.runtime import checkpoint, run_capture, _context, JobCancelled


def test_cache_hit_invalidation_and_corruption(tmp_path, monkeypatch):
    monkeypatch.setenv("KAIROS_CACHE_DIR", str(tmp_path / "cache"))
    video = tmp_path / "source.mp4"
    video.write_bytes(b"original")
    calls = []
    def compute():
        calls.append(1)
        return [{"start": 0, "end": 2, "text": "Hello."}], "en"
    assert cached_transcript(video, "base", compute) == cached_transcript(video, "base", compute)
    assert len(calls) == 1
    cached_transcript(video, "small", compute)
    video.write_bytes(b"changed")
    cached_transcript(video, "base", compute)
    assert len(calls) == 3
    for file in (tmp_path / "cache").rglob("*.json"):
        file.write_text('[]')
    cached_transcript(video, "base", compute)
    assert len(calls) == 4
    monkeypatch.setenv("KAIROS_DISABLE_CACHE", "1")
    cached_transcript(video, "base", compute)
    assert len(calls) == 5


def wait_for(manager, key, states):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status = manager.status(key)
        if status["status"] in states:
            return status
        time.sleep(.01)
    raise AssertionError(manager.status(key))


def test_job_queue_cancel_progress_and_result(tmp_path, monkeypatch):
    from youtube_auto_clipper import discovery
    entered = threading.Event()
    release = threading.Event()
    def operation(source, output_dir="output"):
        checkpoint("transcribing", 20)
        entered.set()
        while not release.wait(.01):
            checkpoint()
        return {"source": source, "output": output_dir}
    monkeypatch.setattr(discovery, "discover_candidates", operation)
    manager = JobManager(tmp_path / "jobs", max_pending=2)
    try:
        first = manager.submit("discover", {"source": "local.mp4"})
        assert entered.wait(2)
        assert manager.status(first["id"])["progress"] == 20
        queued = manager.submit("discover", {"source": "second.mp4"})
        with pytest.raises(ValueError, match="queue is full"):
            manager.submit("discover", {"source": "third.mp4"})
        assert manager.cancel(queued["id"])["status"] == "cancelled"
        assert manager.cancel(first["id"])["cancel_requested"]
        assert wait_for(manager, first["id"], {"cancelled"})["result_path"] is None
        release.set()
        completed = manager.submit("discover", {"source": "last.mp4"})
        result = wait_for(manager, completed["id"], {"completed"})
        assert result["progress"] == 100
        assert json.loads(open(result["result_path"]).read())["source"] == "last.mp4"
        assert manager.cancel(completed["id"])["status"] == "completed"
        with pytest.raises(ValueError, match="Unknown"):
            manager.status("../outside")
    finally:
        release.set()
        manager.close()


def test_failed_job_is_terminal(tmp_path, monkeypatch):
    from youtube_auto_clipper import discovery
    def operation(source, output_dir="output"):
        raise ValueError("secret details must not be serialized")
    monkeypatch.setattr(discovery, "discover_candidates", operation)
    manager = JobManager(tmp_path / "jobs")
    try:
        job = manager.submit("discover", {"source": "bad"})
        status = wait_for(manager, job["id"], {"failed"})
        assert "secret" not in status["error"]
    finally:
        manager.close()


def test_cancel_subprocess_terminates_promptly():
    event = threading.Event()
    token = _context.set((event, lambda *_: None))
    timer = threading.Timer(.2, event.set)
    timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(JobCancelled):
            run_capture([sys.executable, "-c", "import time; time.sleep(60)"])
        assert time.monotonic() - started < 5
    finally:
        timer.cancel()
        _context.reset(token)
