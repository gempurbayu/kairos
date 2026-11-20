"""Reviewable, category-aware candidate discovery for local videos."""
import json
import math
import os
import re
import subprocess
from pathlib import Path

from .pipeline import ai_highlights, select_nonoverlap, transcribe, get_source
from .runtime import checkpoint, run_capture
from .cache import media_hash

MODES = ("auto", "conversation", "instruction", "gaming")
CUES = {
    "conversation": ("why", "because", "story", "imagine", "kenapa", "karena", "cerita"),
    "instruction": ("how", "step", "tip", "tutorial", "fix", "cara", "langkah", "solusi"),
    "gaming": ("clutch", "win", "kill", "boss", "gg", "fail", "menang", "kalah", "anjir"),
}


def validate_options(count, minimum, maximum, mode):
    if (isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 20
            or not math.isfinite(minimum) or not math.isfinite(maximum)
            or minimum <= 0 or maximum < minimum):
        raise ValueError("Use count 1–20 and finite durations with 0 < min <= max")
    if mode not in MODES:
        raise ValueError(f"Mode must be one of {MODES}")


def fingerprint(video):
    """Hash media bytes so plans cannot silently target changed videos."""
    return media_hash(video)


def choose_mode(segments, mode):
    if mode != "auto":
        return mode
    words = re.findall(r"\w+", " ".join(s["text"] for s in segments).lower())
    hits = {name: sum(w in cues for w in words) for name, cues in CUES.items()}
    return max(hits, key=hits.get) if max(hits.values(), default=0) else "conversation"


def media_signals(video, start, end, frames_dir, candidate_id):
    """Sample loudness and frames; these are signals, not event recognition."""
    evidence, warnings, thumbnails = [], [], []
    audio = None
    motion = None
    try:
        result = run_capture(
            ["ffmpeg", "-hide_banner", "-nostats", "-ss", str(start), "-i", str(video),
             "-t", str(end - start), "-vn", "-af", "volumedetect", "-f", "null", "-"],
            timeout=120)
        mean = re.search(r"mean_volume: (-?[\d.]+) dB", result.stderr)
        peak = re.search(r"max_volume: (-?[\d.]+) dB", result.stderr)
        if result.returncode == 0 and mean and peak:
            audio = round(min(100, max(0, (float(peak[1]) - float(mean[1])) * 5)), 1)
            evidence.append("audio_peak_to_mean")
        else:
            warnings.append("No measurable audio dynamics")
    except (OSError, subprocess.TimeoutExpired):
        warnings.append("Audio sampling unavailable")
    try:
        import cv2
        capture = cv2.VideoCapture(str(video))
        samples = []
        try:
            for index, fraction in enumerate((0.15, 0.5, 0.85), 1):
                checkpoint()
                capture.set(cv2.CAP_PROP_POS_MSEC, (start + (end - start) * fraction) * 1000)
                ok, frame = capture.read()
                if not ok:
                    continue
                gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (160, 90))
                samples.append(gray)
                if frames_dir:
                    target = frames_dir / f"{candidate_id}_{index}.jpg"
                    height, width = frame.shape[:2]
                    if cv2.imwrite(str(target), cv2.resize(frame, (480, max(1, round(height * 480 / width))))):
                        thumbnails.append(str(target))
            if len(samples) >= 2:
                motion = round(min(100, sum(float(cv2.absdiff(a, b).mean()) for a, b in zip(samples, samples[1:])) / (len(samples) - 1) / 255 * 100), 1)
                evidence.append("sampled_frame_change")
            else:
                warnings.append("Insufficient readable frames")
        finally:
            capture.release()
    except Exception:
        warnings.append("Frame sampling unavailable")
    return audio, motion, evidence, warnings, thumbnails


def rank_candidates(segments, count, minimum, maximum, mode, goal=""):
    """Create transcript windows with interpretable editorial scores."""
    candidates = []
    goal_words = set(re.findall(r"\w+", goal.lower()))
    for index, segment in enumerate(segments):
        checkpoint()
        texts = []
        for part in segments[index:]:
            duration = part["end"] - segment["start"]
            if duration > maximum:
                break
            texts.append(part["text"])
            if duration < minimum:
                continue
            text = " ".join(texts)
            words = re.findall(r"\w+", text.lower())
            hits = sorted(set(words) & set(CUES[mode]))
            goal_hits = sorted(set(words) & goal_words)
            hook = min(100, len(hits) * 25 + (20 if "?" in text else 0))
            complete = bool(re.search(r"[.!?][\"')\]]*\s*$", text))
            context = 80 if complete else 35
            relevance = min(100, len(goal_hits) / max(1, len(goal_words)) * 100) if goal_words else 50
            pacing = min(100, len(words) / duration / 2.7 * 100)
            score = round(.3 * hook + .3 * context + .2 * relevance + .2 * pacing, 2)
            candidates.append({"start": segment["start"], "end": part["end"],
                               "title": text[:100], "transcript": text,
                               "reason": f"{mode} cues: {', '.join(hits) or 'none'}; sentence ending: {complete}; goal matches: {', '.join(goal_hits) or 'none'}",
                               "score": score, "scores": {"hook": hook, "context": context, "goal_relevance": relevance, "pacing": round(pacing, 1)},
                               "moment_type": {"conversation": "discussion", "instruction": "explanation", "gaming": "commentary_reaction"}[mode]})
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return select_nonoverlap(candidates, count)


def discover_candidates(source, output_dir="candidates", count=5, min_duration=20,
                        max_duration=60, mode="auto", goal="", use_ai=False, model=None,
                        analyze_media=True, allow_download=False):
    checkpoint("validating", 2)
    validate_options(count, min_duration, max_duration, mode)
    video = Path(source).expanduser().resolve()
    if not video.is_file() and not allow_download:
        raise ValueError("Provide a local video or explicitly allow an authorized YouTube download")
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Each plan has its own directory; prior previews are never overwritten.
    import tempfile
    folder = Path(tempfile.mkdtemp(prefix="review-", dir=output))
    if not video.is_file():
        checkpoint("downloading source", 5)
        download_folder = folder / "source"
        download_folder.mkdir()
        video = get_source(source, download_folder, allow_download)
    segments, language = transcribe(video, model or os.getenv("WHISPER_MODEL", "base"))
    checkpoint("ranking candidates", 40)
    resolved_mode = choose_mode(segments, mode)
    clips = rank_candidates(segments, count, min_duration, max_duration, resolved_mode, goal)
    method = "offline"
    warnings = []
    if not clips:
        warnings.append("No speech windows fit the requested duration; try shorter clips or another source")
    if use_ai:
        try:
            ai, method = ai_highlights(segments, count, min_duration, max_duration, resolved_mode, goal)
            # Re-score AI ranges with the same transparent editorial fields.
            if method == "gemini":
                enriched = []
                for item in ai:
                    subset = [s for s in segments if s["start"] >= item["start"] and s["end"] <= item["end"]]
                    ranked = rank_candidates(subset, 1, min_duration, max_duration, resolved_mode, goal)
                    if ranked:
                        enriched.append({**ranked[0], "ai_reason": item["reason"]})
                if enriched:
                    clips = enriched
                else:
                    method = "offline-fallback"
        except Exception:
            method = "offline-fallback"
            warnings.append("AI selection unavailable; used offline scoring")
    for index, clip in enumerate(clips, 1):
        checkpoint(f"sampling candidate {index}/{len(clips)}", 50 + 40 * (index - 1) / len(clips))
        clip["id"] = f"candidate_{index:02d}"
        audio, visual, evidence, issues, thumbs = (media_signals(video, clip["start"], clip["end"], folder, clip["id"])
                                                 if analyze_media else (None, None, [], [], []))
        clip["scores"].update(audio_dynamics=audio, visual_change=visual)
        clip.update(evidence=["transcript"] + evidence, warnings=issues, thumbnails=thumbs,
                    confidence="low" if resolved_mode == "gaming" else "medium")
        if resolved_mode == "gaming":
            clip["warnings"].append("Experimental: does not recognize kills, wins, HUD, or game events")
            clip["score"] = round(.7 * clip["score"] + .2 * (audio or 0) + .1 * (visual or 0), 2)
    clips.sort(key=lambda c: c["score"], reverse=True)
    plan = {"schema_version": 1, "source": str(video), "source_sha256": fingerprint(video),
            "language": language, "mode": resolved_mode, "requested_mode": mode, "goal": goal,
            "method": method, "warnings": warnings, "clips": clips,
            "note": "Editorial signals, not calibrated probabilities or virality predictions. Review before rendering."}
    checkpoint("writing preview", 98)
    path = folder / "candidates.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**plan, "plan_path": str(path)}


def load_selection(plan_path, source, candidate_ids):
    plan = json.loads(Path(plan_path).expanduser().read_text(encoding="utf-8"))
    if plan.get("schema_version") != 1 or fingerprint(source) != plan.get("source_sha256"):
        raise ValueError("Candidate plan does not match this video")
    if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)) or len(candidate_ids) > 20:
        raise ValueError("Select 1–20 unique candidate IDs")
    by_id = {c["id"]: c for c in plan["clips"]}
    if any(key not in by_id for key in candidate_ids):
        raise ValueError("Unknown candidate ID")
    return [by_id[key] for key in candidate_ids]
