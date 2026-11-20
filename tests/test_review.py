import http.client
import json
import threading

import pytest

from youtube_auto_clipper.cache import atomic_json
from youtube_auto_clipper.discovery import fingerprint
from youtube_auto_clipper.review import ReviewServer


@pytest.fixture
def review(video, tmp_path):
    plan = tmp_path / "candidates.json"
    atomic_json(plan, {"schema_version": 1, "source": str(video), "source_sha256": fingerprint(video),
                      "mode": "instruction", "method": "offline", "note": "fixture",
                      "clips": [{"id": "candidate_01", "start": 0, "end": 2,
                                 "title": "<script>untrusted transcript</script>", "transcript": "A tip.",
                                 "reason": "test", "score": 50, "confidence": "medium", "thumbnails": []}]})
    server = ReviewServer(str(video), str(plan))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def request(server, route, method="GET", body=None, token=True, headers=None):
    connection = http.client.HTTPConnection(*server.server_address)
    path = route + (f"?token={server.token}" if token else "")
    headers = {"Content-Type": "application/json", **(headers or {})}
    connection.request(method, path, json.dumps(body) if body is not None else None, headers)
    response = connection.getresponse()
    status, data, response_headers = response.status, response.read(), dict(response.getheaders())
    connection.close()
    return status, data, response_headers


def test_review_requires_token_and_streams_ranges(review):
    assert request(review, "/plan", token=False)[0] == 403
    assert request(review, "/plan", headers={"Host": "attacker.example"})[0] == 403
    status, page, _ = request(review, "/")
    assert status == 200
    assert b"SESSION_TOKEN" not in page
    assert b"untrusted transcript" not in page
    status, data, headers = request(review, "/media", headers={"Range": "bytes=0-15"})
    assert status == 206 and len(data) == 16
    assert headers["Content-Range"].startswith("bytes 0-15/")
    assert request(review, "/media", headers={"Range": "bytes=999999999-"})[0] == 416
    assert request(review, "/../../etc/passwd")[0] == 404


def test_edits_create_revision_without_overwriting_plan(review, monkeypatch):
    captured = []
    monkeypatch.setattr(review.manager, "submit", lambda kind, options: captured.append(options) or {"id": "job"})
    body = {"layout": "fit", "clips": [{"id": "candidate_01", "start": .2, "end": 1.8}]}
    assert request(review, "/render", "POST", body, headers={"Origin": "https://attacker.example"})[0] == 403
    assert request(review, "/render", "POST", body)[0] == 202
    options = captured[0]
    edited = json.loads(open(options["candidate_plan"]).read())
    assert edited["clips"][0]["start"] == .2
    assert json.loads(review.plan_path.read_text())["clips"][0]["start"] == 0
    assert options["layout"] == "fit" and options["face_tracking"] is False
    body["clips"][0]["end"] = 99999
    assert request(review, "/render", "POST", body)[0] == 400


@pytest.mark.parametrize("layout,dimensions", [("fit", (1080, 1920)), ("landscape", (1920, 1080))])
def test_layout_render_preserves_output_shape(video, tmp_path, layout, dimensions):
    import subprocess
    from youtube_auto_clipper.pipeline import render_clip
    output = tmp_path / f"{layout}.mp4"
    render_clip(video, 0, 1, output, layout=layout)
    result = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output)]))
    stream = next(s for s in result["streams"] if s["codec_type"] == "video")
    assert (stream["width"], stream["height"]) == dimensions


def test_abandoned_video_stream_does_not_raise(tmp_path):
    from youtube_auto_clipper.review import ReviewHandler
    media = tmp_path / 'fixture.mp4'
    media.write_bytes(b'fixture media')
    handler = object.__new__(ReviewHandler)
    handler.headers = {}
    handler.send_response = lambda *_: None
    handler.send_header = lambda *_: None
    handler.headers_common = lambda: None
    handler.end_headers = lambda: None
    class Disconnected:
        def write(self, _):
            raise BrokenPipeError('browser abandoned old range')
    handler.wfile = Disconnected()
    handler.send_media(media, 'video/mp4')


def test_review_passes_export_options_and_rejects_conflicts(review, monkeypatch):
    captured = []
    monkeypatch.setattr(review.manager, 'submit', lambda kind, options: captured.append(options) or {'id':'job'})
    body = {'layout':'fit', 'resolution':'720p', 'preset':'tiktok',
            'clips':[{'id':'candidate_01','start':0,'end':2}]}
    assert request(review, '/render', 'POST', body)[0] == 202
    assert captured[0]['resolution'] == '720p'
    assert captured[0]['preset'] == 'tiktok'
    body['layout']='landscape'
    assert request(review, '/render', 'POST', body)[0] == 400
