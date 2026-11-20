"""Local readiness checks. Never download model weights or expose credentials."""
import importlib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from .cache import cache_root
from .runtime import run_capture


def check(name, ok, message, fix="", required=True, warning=False):
    return {"name": name, "status": "ok" if ok else "warning" if warning else "error",
            "message": message, "fix": fix if not ok else "", "required": required}


def probe_media_tools():
    checks = []
    capabilities = {}
    for name in ("ffmpeg", "ffprobe"):
        executable = shutil.which(name)
        if not executable:
            checks.append(check(name, False, f"{name} is not on PATH", "Install FFmpeg with ffprobe and add its bin directory to the harness PATH"))
            continue
        try:
            result = run_capture([executable, "-version"], timeout=10)
            ok = result.returncode == 0
            checks.append(check(name, ok, executable if ok else f"{name} could not start", "Reinstall a working FFmpeg build"))
            if name == "ffmpeg" and ok:
                filters = run_capture([executable, "-hide_banner", "-filters"], timeout=10)
                encoders = run_capture([executable, "-hide_banner", "-encoders"], timeout=10)
                capabilities = {"libass": bool(filters.returncode == 0 and re.search(r"\bass\s+V->V", filters.stdout)),
                                "libx264": bool(encoders.returncode == 0 and re.search(r"\blibx264\s", encoders.stdout)),
                                "aac": bool(encoders.returncode == 0 and re.search(r"\baac\s", encoders.stdout))}
        except Exception as exc:
            # Keep subprocess output and environment secrets out of diagnostics.
            checks.append(check(name, False, f"{name} readiness probe failed ({type(exc).__name__})", "Check the executable and retry"))
    for name, description in (("libass", "burned captions"), ("libx264", "H.264 video"), ("aac", "AAC audio")):
        checks.append(check(name, capabilities.get(name, False),
                            f"FFmpeg {'supports' if capabilities.get(name) else 'is missing support for'} {description}",
                            "Install an FFmpeg build with libass, libx264, and AAC support; restart the harness afterwards"))
    return checks


def require_render_support():
    failures = [item for item in probe_media_tools() if item["status"] == "error"]
    if failures:
        details = "; ".join(item["message"] for item in failures)
        raise RuntimeError(f"Render prerequisites failed: {details}. Run 'kairos doctor' for fixes")


def writable(path):
    try:
        parent = Path(path).expanduser().resolve()
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        with tempfile.TemporaryFile(dir=parent):
            return True
    except (OSError, RuntimeError):
        return False


def local_model_ready(model):
    """Only inspect local model files; local_files_only forbids a network fetch."""
    from faster_whisper.utils import download_model
    path = Path(model).expanduser()
    if not path.is_dir():
        path = Path(download_model(model, local_files_only=True))
    return all((path / name).is_file() for name in ("model.bin", "config.json", "tokenizer.json"))


def diagnose(model=None, output_dir="output", jobs_dir=None):
    model = model or os.getenv("WHISPER_MODEL", "base")
    checks = [check("python", sys.version_info >= (3, 10), sys.version.split()[0], "Use Python 3.10 or newer")]
    checks.extend(probe_media_tools())
    whisper = False
    try:
        importlib.import_module("faster_whisper")
        whisper = True
    except Exception:
        pass
    checks.append(check("transcription", whisper, "Local transcription dependencies load" if whisper else "Local transcription dependencies cannot load", "Reinstall Kairos in a supported Python environment"))
    detector = False
    try:
        cv2 = importlib.import_module("cv2")
        detector = hasattr(cv2, "CascadeClassifier") and not cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml").empty()
    except Exception:
        pass
    checks.append(check("face_detector", detector, "Face detector available" if detector else "Face tracking unavailable; portrait uses a centered fallback", "Upgrade Kairos and use its OpenCV 4.x dependency", required=False, warning=True))
    for name, path in (("output_writable", output_dir), ("cache_writable", cache_root()),
                       ("jobs_writable", jobs_dir or os.getenv("KAIROS_JOBS_DIR", str(Path.home()/".cache"/"kairos"/"jobs")))):
        checks.append(check(name, writable(path), str(Path(path).expanduser()), "Choose a writable directory using --output, KAIROS_CACHE_DIR, or KAIROS_JOBS_DIR", required=name != "cache_writable", warning=name == "cache_writable"))
    cached = False
    if whisper:
        try:
            cached = local_model_ready(model)
        except Exception:
            pass
    checks.append(check("model_cached", cached, f"Model {model}: {'cached locally' if cached else 'not confirmed in the local cache'}", "The first transcription needs internet to download model weights, or provide a complete local model directory", required=False, warning=True))
    ready = all(c["status"] == "ok" for c in checks if c["required"])
    return {"ready": ready, "offline_ready": ready and cached, "face_tracking_ready": detector,
            "status": "blocked" if not ready else "warning" if any(c["status"] == "warning" for c in checks) else "ready",
            "checks": checks, "network_used": False,
            "gemini_configured": bool(os.getenv("GEMINI_API_KEY")), "note": "Checks inspect prerequisites; they do not validate API credentials or download models"}


def doctor_cli(argv):
    import argparse
    import json
    parser = argparse.ArgumentParser(prog="kairos doctor", description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable diagnostics")
    parser.add_argument("--model", default=None)
    parser.add_argument("--output", default="output")
    args = parser.parse_args(argv)
    report = diagnose(args.model, args.output)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Kairos doctor: {report['status']}")
        for item in report["checks"]:
            print(f"[{item['status'].upper()}] {item['name']}: {item['message']}")
            if item["fix"]:
                print(f"  Fix: {item['fix']}")
        print(f"Offline ready: {report['offline_ready']}")
    if not report["ready"]:
        raise SystemExit(1)
