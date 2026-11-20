"""Cooperative cancellation and phase progress for synchronous pipeline code."""
from contextvars import ContextVar


class JobCancelled(BaseException):
    """Separate from ordinary failures so fallback handlers never swallow cancellation."""


_context = ContextVar("kairos_job_context", default=None)


def checkpoint(stage=None, progress=None):
    context = _context.get()
    if context:
        cancelled, update = context
        if cancelled.is_set():
            raise JobCancelled()
        if stage is not None:
            update(stage, progress)


def run_capture(args, timeout=None):
    """Poll subprocesses so cancelled jobs terminate and reap their child process."""
    import subprocess
    import time
    checkpoint()
    started = time.monotonic()
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        while True:
            checkpoint()
            if timeout is not None and time.monotonic() - started > timeout:
                raise subprocess.TimeoutExpired(args, timeout)
            try:
                stdout, stderr = process.communicate(timeout=0.2)
                return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                continue
    except BaseException:
        process.terminate()
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
        raise
