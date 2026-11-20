# Candidate quality evaluation

Synthetic integration checks verify software behavior, not whether real highlights are good. An authorized five-minute gaming excerpt is used for an initial local smoke evaluation in this development cycle. That is not a benchmark across categories. Do not report synthetic scores as real-world quality results or claim quality improvements without reference annotations.

## Automated checks

`python -m pytest -q` covers cache reuse/invalidation/corruption, queued and running cancellation, job progress/failures, subprocess termination, and candidate selection. The media tests create a short test-pattern video and sine-wave audio at runtime. They replace speech inference with a deterministic transcript so they do not download model weights or contact a service.

The media suite also exercises real stdio MCP initialization/tool calls, asynchronous discovery, and selected rendering. Full caption rendering requires FFmpeg with libass; tests skip that branch if it is unavailable locally. GitHub Actions installs Ubuntu FFmpeg to run caption rendering in CI. These checks do not measure Whisper transcription accuracy.

## Evaluate authorized real videos

Use at least one conversation, instruction, and commented-gaming source that you own or have permission to process. Keep the source videos and their annotations outside Git.

1. Watch each source and mark interesting moments before seeing Kairos's predictions.
2. Discover five candidates with a fixed mode, goal, and duration range. Record whether offline or Gemini selection was used.
3. Copy the plan's `source_sha256` into a private annotations JSON file. Add the reference moments in seconds:

```json
{
  "source_sha256": "COPY_FROM_CANDIDATES_JSON",
  "moments": [
    {"start": 30, "end": 55},
    {"start": 120, "end": 150}
  ]
}
```

4. Run `python scripts/evaluate_candidates.py /path/to/candidates.json /path/to/annotations.json --top-n 5`.
5. Review every candidate for relevance, opening context, complete ending, misleading edits, framing, and readable captions. Record good/bad decisions and a short reason.
6. Compare changes using the same sources, annotations, mode, goal, and duration settings. Keep missed moments as regression examples.

The script reports interval precision and reference-moment recall with an intersection-over-union threshold of 0.3. A match only means temporal overlap, not a good editorial cut. It checks the source hashes match. Human review remains necessary, especially for gaming events without speech or information at the screen edges.

## Review studio checks

The review HTTP tests check token/host/origin validation, media byte-range streaming, immutable edited plans, invalid timestamp rejection, and output dimensions for fit/landscape layouts. Browser inspection should additionally cover desktop/mobile widths, actual source playback, selecting candidates, editing timestamps, and rendering status/results. The source player is not a simulation of the final layout. Confirm the final MP4 before sharing.

## Initial real-source smoke evaluation

A five-minute authorized excerpt of a gaming livestream was transcribed locally with Whisper `base` and analyzed in gaming mode. Discovery produced five candidates, and one selected candidate was rendered with full-frame portrait padding and captions. The source and generated artifacts stay outside Git.

The sampled interval primarily contained live-chat discussion rather than gameplay. All five candidates had low confidence, no matched gaming keywords, and no matches for the supplied English editorial goal in the Indonesian transcript. This verifies the pipeline on real media but does not demonstrate gameplay-event detection or good editorial selection. Reference timestamps have not been annotated, so no precision/recall claim is made.

Follow-up evaluation should cover actual gameplay intervals, goals in the transcript language, slang transcription accuracy, complete opening/ending context, and caption review. Do not infer segment content solely from the video title or category.

## Editorial selector v2 smoke comparison

Re-running the same cached transcript with the same English goal produced five candidates labeled as conversation, with mismatch warnings for the requested gaming mode. Common reaction concepts matched in all five, where literal matching previously yielded zero goal matches. This is evidence that bilingual concept matching and mismatch reporting execute; it is not a measured improvement in highlight quality. ASR wording errors and context dependence remain visible and still require manual review.

Authored English/Indonesian regression examples test question/answer grouping, fragment merging, unpunctuated fallback, repetition/CTA suppression, mixed-content penalties, ambiguous workplace/game terms, and AI range alignment/deduplication. These synthetic expectations do not substitute for human annotations on varied real sources.
