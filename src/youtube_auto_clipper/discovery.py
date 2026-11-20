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
from .editorial import detect_content, speech_units, score_window

MODES = ("auto", "conversation", "instruction", "gaming")


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
    detected, _ = detect_content(" ".join(s["text"] for s in segments))
    return "conversation" if detected == "unknown" else detected


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


def candidate_pool(segments, minimum, maximum, mode, goal=""):
    units = speech_units(segments, maximum=maximum)
    candidates = []
    for index, unit in enumerate(units):
        checkpoint()
        for last in range(index, len(units)):
            duration = units[last]["end"] - unit["start"]
            if duration > maximum:
                break
            if duration >= minimum:
                candidates.append(score_window(units[index:last + 1], mode, goal))
    return candidates


def rank_candidates(segments, count, minimum, maximum, mode, goal=""):
    """Rank complete utterance windows using bilingual, inspectable concepts."""
    candidates = candidate_pool(segments, minimum, maximum, mode, goal)
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return select_nonoverlap(candidates, count)


def align_ai_candidate(segments, proposal, minimum, maximum, mode, goal):
    # Reuse transcript timing/boundary evidence rather than trusting generated ranges.
    candidates = candidate_pool(segments, minimum, maximum, mode, goal)
    def overlap(item):
        return max(0, min(item["end"], proposal["end"]) - max(item["start"], proposal["start"])) / (max(item["end"], proposal["end"]) - min(item["start"], proposal["start"]))
    eligible = [c for c in candidates if overlap(c) >= .5]
    if not eligible:
        return None
    chosen = max(eligible, key=lambda c: (overlap(c) + c["scores"]["context"] / 1000, c["score"]))
    return {**chosen, "ai_reason": proposal["reason"],
            "ai_proposal": {"start": proposal["start"], "end": proposal["end"]}}


def select_editorial_highlights(segments, count, minimum, maximum, mode="auto", goal="",
                               use_ai=False, ai_selector=None):
    """One selection policy shared by discovery, direct rendering, and MCP."""
    validate_options(count, minimum, maximum, mode)
    offline = rank_candidates(segments, count, minimum, maximum, mode, goal)
    if not use_ai:
        return offline, "offline", []
    selector = ai_selector or ai_highlights
    try:
        proposals, method = selector(segments, count, minimum, maximum, mode, goal)
        if method != "gemini":
            return offline, method, []
        aligned = [align_ai_candidate(segments, c, minimum, maximum, mode, goal) for c in proposals]
        aligned = sorted((c for c in aligned if c), key=lambda c: c["score"], reverse=True)
        clips = select_nonoverlap(aligned, count)
        if clips:
            return clips, "gemini", []
    except Exception:
        pass
    return offline, "offline-fallback", ["AI selection unavailable or invalid; used offline scoring"]


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
    clips, method, warnings = select_editorial_highlights(segments, count, min_duration,
                                                          max_duration, mode, goal, use_ai)
    if not clips:
        warnings.append("No speech windows fit the requested duration; try shorter clips or another source")
    for index, clip in enumerate(clips, 1):
        checkpoint(f"sampling candidate {index}/{len(clips)}", 50 + 40 * (index - 1) / len(clips))
        clip["id"] = f"candidate_{index:02d}"
        audio, visual, evidence, issues, thumbs = (media_signals(video, clip["start"], clip["end"], folder, clip["id"])
                                                 if analyze_media else (None, None, [], [], []))
        clip["scores"].update(audio_dynamics=audio, visual_change=visual)
        clip.update(evidence=["transcript"] + evidence, warnings=clip["warnings"] + issues, thumbnails=thumbs,
                    confidence="low" if mode == "gaming" or clip["content_mode"] in ("gaming", "unknown") or clip["warnings"] else "medium")
        if mode == "gaming" or clip["content_mode"] == "gaming":
            clip["warnings"].append("Experimental: does not recognize kills, wins, HUD, or game events")
            # Audio/frame changes corroborate a transcript shortlist; they cannot
            # turn unsupported chatter into a high-scoring gameplay event.
            if clip["content_mode"] == "gaming":
                clip["score"] = round(.9 * clip["score"] + .07 * (audio or 0) + .03 * (visual or 0), 2)
    clips.sort(key=lambda c: c["score"], reverse=True)
    plan = {"schema_version": 1, "source": str(video), "source_sha256": fingerprint(video),
            "language": language, "mode": resolved_mode, "requested_mode": mode, "goal": goal,
            "method": method, "warnings": warnings, "clips": clips,
            "analysis": {"version": 2, "goal_matching": "English/Indonesian concept lexicon plus literal terms",
                         "segment_classification": "transcript cues only; no visual event recognition",
                         "boundaries": "ASR punctuation and speech pauses; not guaranteed semantic completeness"},
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
