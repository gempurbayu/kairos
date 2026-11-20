"""Loopback-only review server for a single local source and candidate plan."""
import copy
import hmac
import json
import math
import mimetypes
import re
import secrets
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .cache import atomic_json
from .discovery import fingerprint
from .jobs import JobManager
from .export import export_target
from .pipeline import run_command


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, source, plan_path, port=0, resolution="1080p", preset=None, layout=None):
        export_target(layout or "portrait", resolution, preset)
        self.defaults = {"resolution": resolution, "preset": preset, "layout": layout}
        self.source = Path(source).expanduser().resolve()
        self.plan_path = Path(plan_path).expanduser().resolve()
        self.plan = json.loads(self.plan_path.read_text(encoding="utf-8"))
        if self.plan.get("schema_version") != 1 or self.plan.get("source_sha256") != fingerprint(self.source):
            raise ValueError("Plan does not match this source video")
        self.duration = float(json.loads(run_command(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(self.source)]))["format"]["duration"])
        if not math.isfinite(self.duration) or self.duration <= 0:
            raise ValueError("Source must have a finite positive duration")
        self.token = secrets.token_urlsafe(32)
        self.manager = JobManager(root=self.plan_path.parent / "renders")
        self.edit_lock = threading.Lock()
        super().__init__(("127.0.0.1", port), ReviewHandler)
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"

    @property
    def url(self):
        return f"{self.origin}/?token={self.token}"

    def start_render(self, edits, layout, resolution="1080p", preset=None, preview_seconds=None):
        export_target(layout, resolution, preset)
        if not isinstance(edits, list) or not 1 <= len(edits) <= 20:
            raise ValueError("Select 1–20 candidates")
        if preview_seconds is not None:
            if len(edits) != 1 or not isinstance(preview_seconds, (int, float)) or isinstance(preview_seconds, bool) or not math.isfinite(preview_seconds) or not 1 <= preview_seconds <= 10:
                raise ValueError("Preview requires one candidate and a length of 1–10 seconds")
        by_id = {clip["id"]: clip for clip in self.plan["clips"]}
        chosen, seen = [], set()
        for edit in edits:
            key = edit["id"]
            if key not in by_id or key in seen:
                raise ValueError("Select unique known candidate IDs")
            seen.add(key)
            start, end = float(edit["start"]), float(edit["end"])
            if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= self.duration):
                raise ValueError("Timestamps must be inside the video with start < end")
            chosen.append({**by_id[key], "start": start, "end": end, "reviewed": True})
        # Preserve the original preview and save immutable revisions per render request.
        revised = copy.deepcopy(self.plan)
        revised["clips"] = chosen
        revised["source"] = str(self.source)
        path = self.plan_path.parent / f"reviewed-{uuid.uuid4().hex}.json"
        with self.edit_lock:
            atomic_json(path, revised)
            if preview_seconds is not None:
                return self.manager.submit("preview", {"source": str(self.source),
                    "candidate_plan": str(path), "candidate_id": chosen[0]["id"], "seconds": preview_seconds,
                    "layout": layout, "face_tracking": layout == "portrait",
                    "resolution": resolution, "preset": preset})
            return self.manager.submit("render", {"source": str(self.source),
                "candidate_plan": str(path), "candidate_ids": [c["id"] for c in chosen],
                "layout": layout, "face_tracking": layout == "portrait",
                "resolution": resolution, "preset": preset})

    def server_close(self):
        self.manager.close()
        super().server_close()


class ReviewHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Request URLs contain a session token.

    def reply(self, status, data, content_type="application/json"):
        payload = json.dumps(data, ensure_ascii=False).encode() if content_type == "application/json" else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.headers_common()
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def headers_common(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; media-src 'self'; connect-src 'self'; frame-ancestors 'none'")

    def authorized(self):
        parts = urlsplit(self.path)
        supplied = parse_qs(parts.query).get("token", [""])[0]
        if self.headers.get("Host") != urlsplit(self.server.origin).netloc:
            self.reply(403, {"error": "Invalid host"})
            return False
        if not hmac.compare_digest(supplied.encode(), self.server.token.encode()):
            self.reply(403, {"error": "Invalid session token"})
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.origin:
            self.reply(403, {"error": "Invalid origin"})
            return False
        return True

    def send_media(self, path, content_type):
        size = path.stat().st_size
        start, end = 0, size - 1
        request_range = self.headers.get("Range")
        if request_range:
            match = re.fullmatch(r"bytes=(\d+)-(\d*)", request_range)
            if not match:
                self.reply(416, {"error": "Unsupported byte range"})
                return
            start = int(match[1])
            end = min(size - 1, int(match[2]) if match[2] else size - 1)
            if start > end or start >= size:
                self.reply(416, {"error": "Range outside file"})
                return
        self.send_response(206 if request_range else 200)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if request_range:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.headers_common()
        self.end_headers()
        with path.open("rb") as stream:
            stream.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = stream.read(min(left, 1024 * 1024))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_GET(self):
        if not self.authorized():
            return
        route = urlsplit(self.path).path
        try:
            if route == "/doctor":
                from .doctor import diagnose
                self.reply(200, diagnose(output_dir=str(self.server.plan_path.parent), jobs_dir=self.server.manager.root))
            elif route == "/plan":
                self.reply(200, {**self.server.plan, "duration": self.server.duration, "export_defaults": self.server.defaults})
            elif route in ("/", "/app.js", "/style.css"):
                name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[route]
                content_type = {"/": "text/html; charset=utf-8", "/app.js": "text/javascript", "/style.css": "text/css"}[route]
                data = files("youtube_auto_clipper").joinpath("web", name).read_bytes()
                # Static assets need the same session token, never source/transcript interpolation.
                if route == "/":
                    data = data.replace(b"SESSION_TOKEN", self.server.token.encode())
                self.reply(200, data, content_type)
            elif route == "/media":
                self.send_media(self.server.source, mimetypes.guess_type(str(self.server.source))[0] or "application/octet-stream")
            elif route.startswith("/thumbnail/"):
                _, _, key, index = route.split("/")
                clip = next(c for c in self.server.plan["clips"] if c["id"] == key)
                path = Path(clip["thumbnails"][int(index)]).resolve()
                if not path.is_relative_to(self.server.plan_path.parent) or path.suffix.lower() != ".jpg":
                    raise ValueError("Thumbnail outside review folder")
                self.send_media(path, "image/jpeg")
            elif route.startswith("/artifact/"):
                _, _, key, index, kind = route.split("/")
                if kind not in ("video", "subtitles"):
                    raise ValueError("Unknown artifact")
                job = self.server.manager.status(key)
                if job["status"] != "completed":
                    raise ValueError("Job is not complete")
                manifest = json.loads(Path(job["result_path"]).read_text())
                path = Path(manifest["clips"][int(index)][kind]).resolve()
                if not path.is_relative_to(Path(job["output_dir"]).resolve()):
                    raise ValueError("Artifact outside job output")
                self.send_media(path, "video/mp4" if kind == "video" else "application/x-subrip")
            elif route.startswith("/jobs/"):
                key = route.removeprefix("/jobs/")
                job = self.server.manager.status(key)
                if job["status"] == "completed":
                    job["result"] = json.loads(Path(job["result_path"]).read_text())
                self.reply(200, job)
            else:
                self.reply(404, {"error": "Not found"})
        except (BrokenPipeError, ConnectionResetError):
            return
        except (ValueError, KeyError, IndexError, StopIteration, OSError):
            self.reply(400, {"error": "Requested resource is not available"})

    def do_POST(self):
        if not self.authorized():
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 64 * 1024 or self.headers.get_content_type() != "application/json":
                raise ValueError("Expected a small JSON request")
            body = json.loads(self.rfile.read(length))
            route = urlsplit(self.path).path
            if route in ("/render", "/preview"):
                self.reply(202, self.server.start_render(body["clips"], body["layout"],
                                                              body.get("resolution", "1080p"), body.get("preset"),
                                                              body.get("seconds", 5) if route == "/preview" else None))
            elif route == "/cancel":
                self.reply(200, self.server.manager.cancel(body["job_id"]))
            else:
                self.reply(404, {"error": "Not found"})
        except (ValueError, KeyError, TypeError, OSError):
            self.reply(400, {"error": "Invalid request: check timestamps, candidates, layout, and preview length (1–10 seconds)"})


def serve_review(source, plan_path, port=0, resolution="1080p", preset=None, layout=None):
    server = ReviewServer(source, plan_path, port, resolution, preset, layout)
    print(f"Kairos review: {server.url}", flush=True)
    webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
