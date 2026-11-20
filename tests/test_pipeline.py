from youtube_auto_clipper.pipeline import srt_timestamp, fallback_highlights, select_nonoverlap

def test_timestamp():
    assert srt_timestamp(61.234) == "00:01:01,234"

def test_no_overlap():
    candidates = [{"start": 0, "end": 25, "score": 10},
                  {"start": 5, "end": 30, "score": 9},
                  {"start": 30, "end": 55, "score": 8}]
    assert len(select_nonoverlap(candidates, 2)) == 2

def test_fallback():
    segments = [{"start": 0, "end": 12, "text": "hello " * 30},
                {"start": 12, "end": 25, "text": "world " * 30}]
    assert len(fallback_highlights(segments, 1, 20, 30)) == 1
