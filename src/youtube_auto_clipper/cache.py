"""Content-addressed transcript cache with atomic private writes."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .runtime import checkpoint

CACHE_VERSION = 1


def media_hash(video):
    digest = hashlib.sha256()
    with Path(video).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checkpoint()
            digest.update(chunk)
    return digest.hexdigest()


def cache_root():
    return Path(os.getenv("KAIROS_CACHE_DIR", str(Path.home() / ".cache" / "kairos"))).expanduser()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".kairos-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def valid_transcript(segments, language):
    import math
    if not isinstance(segments, list) or not isinstance(language, str):
        return False
    previous = 0
    try:
        for segment in segments:
            start, end = segment["start"], segment["end"]
            if not (math.isfinite(start) and math.isfinite(end) and previous <= start < end
                    and isinstance(segment["text"], str)):
                return False
            previous = start
            for word in segment.get("words", []):
                if not (math.isfinite(word["start"]) and math.isfinite(word["end"])
                        and word["start"] <= word["end"] and isinstance(word["text"], str)):
                    return False
    except (TypeError, KeyError):
        return False
    return True


def cached_transcript(video, model, compute):
    if os.getenv("KAIROS_DISABLE_CACHE", "").lower() in ("1", "true"):
        return compute()
    digest = media_hash(video)
    # Include implementation settings so changes never reuse incompatible results.
    from importlib.metadata import version, PackageNotFoundError
    try:
        engine = version("faster-whisper")
    except PackageNotFoundError:
        engine = "unknown"
    identity = {"schema": CACHE_VERSION, "source": digest, "model": model,
                "engine": engine, "device": "cpu", "compute_type": "int8",
                "beam_size": 5, "vad_filter": True, "word_timestamps": True}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    path = cache_root() / "transcripts" / f"{key}.json"
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(saved, dict) and saved.get("identity") == identity and valid_transcript(saved["segments"], saved["language"]):
            return saved["segments"], saved["language"]
    except (OSError, ValueError, TypeError, KeyError):
        pass
    segments, language = compute()
    checkpoint()
    if media_hash(video) != digest:
        raise ValueError("Source video changed during transcription; retry with a stable file")
    if valid_transcript(segments, language):
        try:
            atomic_json(path, {"identity": identity, "segments": segments, "language": language})
        except OSError:
            # Read-only cache locations must not prevent local processing.
            pass
    return segments, language
