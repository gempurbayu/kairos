"""Bounded session-scoped background jobs for an MCP server."""
import copy
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .cache import atomic_json
from .runtime import JobCancelled, _context, checkpoint

TERMINAL = {"completed", "failed", "cancelled"}


def now():
    return datetime.now(timezone.utc).isoformat()


class JobManager:
    def __init__(self, root=None, max_pending=8):
        self.root = Path(root or os.getenv("KAIROS_JOBS_DIR", str(Path.home() / ".cache" / "kairos" / "jobs"))).expanduser()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kairos")
        self.lock = threading.RLock()
        self.jobs = {}
        self.max_pending = max_pending

    def _save(self, job):
        try:
            atomic_json(self.root / job["id"] / "status.json", job)
        except OSError:
            job["persistence_warning"] = "Status snapshot could not be saved; status is available in memory"

    def submit(self, kind, options):
        if kind not in ("discover", "render"):
            raise ValueError("Job kind must be discover or render")
        # Only allow parameters the public pipeline actually accepts.
        from inspect import signature
        from .discovery import discover_candidates
        from .pipeline import process
        operation = discover_candidates if kind == "discover" else process
        signature(operation).bind(**options)
        with self.lock:
            if sum(item["status"] not in TERMINAL for item, _ in self.jobs.values()) >= self.max_pending:
                raise ValueError("Job queue is full; wait or cancel a pending job")
            key = uuid.uuid4().hex
            folder = self.root / key
            options = dict(options)
            # A job never overwrites a previous job's output.
            options["output_dir"] = str(folder / "output")
            job = {"id": key, "kind": kind, "status": "queued", "stage": "queued",
                   "progress": 0, "created_at": now(), "updated_at": now(),
                   "output_dir": options["output_dir"], "result_path": None,
                   "cancel_requested": False, "error": None}
            self._save(job)
            event = threading.Event()
            self.jobs[key] = (job, event)
            self.executor.submit(self._run, key, operation, options)
            return copy.deepcopy(job)

    def _run(self, key, operation, options):
        with self.lock:
            job, event = self.jobs[key]
            if event.is_set():
                return
            job.update(status="running", stage="starting", updated_at=now())
            self._save(job)
        def update(stage, progress):
            with self.lock:
                job.update(stage=stage, updated_at=now())
                if progress is not None:
                    job["progress"] = min(99, max(job["progress"], progress))
                self._save(job)
        token = _context.set((event, update))
        try:
            checkpoint()
            result = operation(**options)
            checkpoint()
            path = self.root / key / "result.json"
            atomic_json(path, result)
            with self.lock:
                # Serialize completion and cancellation so neither can overwrite the other.
                if event.is_set():
                    raise JobCancelled()
                job.update(status="completed", stage="completed", progress=100,
                           result_path=str(path), updated_at=now())
                self._save(job)
        except JobCancelled:
            with self.lock:
                job.update(status="cancelled", stage="cancelled", updated_at=now())
                self._save(job)
        except Exception as exc:
            message = f"{type(exc).__name__}: job failed; check media and tool prerequisites"
            if isinstance(exc, RuntimeError) and str(exc).startswith("FFmpeg needs the ass/libass"):
                message = "FFmpeg needs the ass/libass subtitle filter; install a build with libass and retry"
            with self.lock:
                job.update(status="failed", stage="failed", error=message, updated_at=now())
                self._save(job)
        finally:
            _context.reset(token)

    def status(self, key):
        with self.lock:
            if key not in self.jobs:
                raise ValueError("Unknown job ID in this MCP server session")
            return copy.deepcopy(self.jobs[key][0])

    def cancel(self, key):
        with self.lock:
            if key not in self.jobs:
                raise ValueError("Unknown job ID in this MCP server session")
            job, event = self.jobs[key]
            if job["status"] not in TERMINAL:
                event.set()
                job.update(cancel_requested=True, updated_at=now())
                if job["status"] == "queued":
                    job.update(status="cancelled", stage="cancelled")
                self._save(job)
            return copy.deepcopy(job)

    def close(self):
        with self.lock:
            for key in list(self.jobs):
                self.cancel(key)
        self.executor.shutdown(wait=True)
