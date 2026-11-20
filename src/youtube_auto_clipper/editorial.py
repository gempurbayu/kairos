"""Explainable English/Indonesian editorial signals, not general semantic understanding."""
import re

from .runtime import checkpoint

# Shared concept IDs make common editorial goals comparable across English/Indonesian.
CONCEPTS = {
    "humor": ("funny", "humor", "joke", "laugh", "lucu", "ngakak", "ketawa", "kocak", "bercanda"),
    "reaction": ("reaction", "react", "surprised", "surprising", "wow", "reaksi", "kaget", "terkejut", "aduh", "anjir"),
    "failure": ("fail", "failed", "mistake", "error", "gagal", "kesalahan", "salah", "kalah"),
    "success": ("clutch", "comeback", "win", "won", "victory", "menang", "berhasil", "kemenangan"),
    "instruction": ("tutorial", "tip", "tips", "step", "steps", "how", "fix", "solution", "useful", "teach", "teaching", "cara", "langkah", "solusi", "berguna", "perbaiki", "mengatasi"),
    "story": ("story", "experience", "lesson", "cerita", "pengalaman", "pelajaran"),
    "explanation": ("why", "because", "reason", "explain", "kenapa", "mengapa", "karena", "alasan", "jelaskan"),
    "gameplay": ("gameplay", "kill", "headshot", "shoot", "enemy", "boss", "nembak", "tembak", "musuh", "nyawa", "peluru"),
    "chat": ("chat", "chatting", "spoiler", "podcast", "interview", "obrolan", "ngobrol", "ngomong", "wawancara"),
}
TERMINAL = re.compile(r"[.!?][\"')\]]*\s*$")
DEPENDENT = {"and", "but", "because", "then", "that", "dan", "tapi", "karena", "terus", "itu", "dia"}
CTA = {"subscribe", "subscribers", "likes", "like", "follow", "donate", "donasi", "langganan"}


def words(text):
    return re.findall(r"\w+", text.casefold())


def concepts(text):
    tokens = set(words(text))
    return {key for key, synonyms in CONCEPTS.items() if tokens.intersection(synonyms)}


def detect_content(text):
    hits = concepts(text)
    # A reaction or swear word alone is not evidence of gameplay.
    strong_gameplay = set(words(text)) & {"clutch", "headshot", "gameplay", "kill", "nembak", "peluru"}
    if strong_gameplay or {"gameplay", "success"}.issubset(hits):
        return "gaming", sorted(hits & {"gameplay", "success"})
    if "instruction" in hits:
        return "instruction", ["instruction"]
    if hits & {"chat", "story", "explanation", "humor", "reaction"}:
        return "conversation", sorted(hits & {"chat", "story", "explanation", "humor", "reaction"})
    return "unknown", []


def speech_units(segments, pause=.8, maximum=60):
    """Group ASR fragments until punctuation or a pause; retain timing evidence."""
    units = []
    current = None
    for index, segment in enumerate(segments):
        checkpoint()
        start, end = segment["start"], segment["end"]
        previous = segments[index - 1] if index else None
        gap_before = start - previous["end"] if previous else None
        clean_start = previous is None or bool(TERMINAL.search(previous["text"])) or gap_before >= pause
        if current is None:
            current = {"start": start, "end": end, "text": segment["text"], "start_clean": clean_start,
                       "start_evidence": "source_start" if previous is None else "sentence_or_pause" if clean_start else "fragment"}
        else:
            current["end"] = end
            current["text"] += " " + segment["text"]
        following = segments[index + 1] if index + 1 < len(segments) else None
        limit = following is not None and following["end"] - current["start"] > maximum
        punctuated = bool(TERMINAL.search(segment["text"]))
        paused = following is not None and following["start"] - end >= pause
        if punctuated or paused or limit or following is None:
            current.update(end_clean=punctuated or paused,
                           end_evidence="punctuation" if punctuated else "pause" if paused else "duration_limit" if limit else "source_end_unconfirmed")
            units.append(current)
            current = None
    return units


def score_window(units, mode, goal):
    text = " ".join(unit["text"] for unit in units)
    tokens = words(text)
    hits = concepts(text)
    requested = concepts(goal)
    literal = set(words(goal)) - {"find", "clips", "clip", "moments", "moment", "cari", "klip", "momen", "yang"}
    matches = requested & hits
    literal_hits = literal & set(tokens)
    goal_relevance = 100 * len(matches) / len(requested) if requested else 100 * len(literal_hits) / max(1, len(literal)) if literal else 50
    detected, evidence = detect_content(text)
    active_mode = detected if mode == "auto" and detected != "unknown" else mode if mode != "auto" else "conversation"
    category = {"conversation": {"chat", "story", "explanation", "humor", "reaction"},
                "instruction": {"instruction", "explanation", "failure"},
                "gaming": {"gameplay", "success", "failure", "reaction", "humor"}}[active_mode]
    category_hits = hits & category
    start_clean, end_clean = units[0]["start_clean"], units[-1]["end_clean"]
    dependent = bool(tokens and tokens[0] in DEPENDENT)
    open_question = text.rstrip().endswith("?")
    context = max(0, (50 if start_clean else 15) + (50 if end_clean else 10) - (20 if dependent else 0) - (20 if open_question else 0))
    duration = units[-1]["end"] - units[0]["start"]
    pacing = min(100, len(tokens) / duration / 2.7 * 100)
    hook = min(100, len(category_hits) * 25)
    repetition = 100 * (1 - len(set(tokens)) / max(1, len(tokens)))
    cta = min(35, sum(token in CTA for token in tokens) * 7)
    penalty = max(0, repetition - 55) + cta
    unit_modes = {detect_content(unit["text"])[0] for unit in units} - {"unknown"}
    transition_penalty = max(0, len(unit_modes) - 1) * 15
    matched_terms = sorted(set(tokens) & {term for concept in category_hits for term in CONCEPTS[concept]})
    mismatch = mode != "auto" and detected not in (mode, "unknown")
    score = max(0, .25 * hook + .35 * context + .25 * goal_relevance + .15 * pacing - penalty - transition_penalty - (10 if mismatch else 0))
    warnings = []
    if not start_clean or dependent:
        warnings.append("Opening may depend on previous context")
    if not end_clean or open_question:
        warnings.append("Ending may be incomplete or need an answer")
    if transition_penalty:
        warnings.append("Window spans different transcript content types; check the topic transition")
    if mismatch:
        warnings.append(f"Requested {mode}, but transcript suggests {detected}; verify segment content")
    if (requested or literal) and not matches and not literal_hits:
        warnings.append("No supported goal concepts matched")
    if detected == "unknown":
        warnings.append("Insufficient transcript evidence to classify segment")
    return {"start": units[0]["start"], "end": units[-1]["end"], "title": text[:100], "transcript": text,
            "score": round(score, 2), "content_mode": detected, "classification_evidence": evidence, "matched_terms": matched_terms,
            "goal_matches": sorted(matches), "boundary": {"start": units[0]["start_evidence"], "end": units[-1]["end_evidence"],
                                                         "start_clean": start_clean and not dependent, "end_clean": end_clean and not open_question},
            "scores": {"hook": hook, "context": context, "goal_relevance": round(goal_relevance, 1),
                       "pacing": round(pacing, 1), "repetition_penalty": round(penalty, 1), "transition_penalty": transition_penalty},
            "reason": f"Content: {detected}; concepts: {', '.join(sorted(category_hits)) or 'none'}; matched terms: {', '.join(matched_terms) or 'none'}; goal matches: {', '.join(sorted(matches)) or ', '.join(sorted(literal_hits)) or 'none'}; boundaries: {units[0]['start_evidence']} / {units[-1]['end_evidence']}",
            "warnings": warnings,
            "confidence": "low" if warnings or detected in ("gaming", "unknown") else "medium",
            "moment_type": {"conversation": "discussion", "instruction": "explanation", "gaming": "commentary_reaction"}[active_mode]}
