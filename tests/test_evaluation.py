import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("evaluate_candidates", Path(__file__).resolve().parents[1] / "scripts" / "evaluate_candidates.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_interval_evaluation_counts_misses_and_irrelevant_candidates():
    plan = {"source_sha256": "same", "clips": [
        {"id": "a", "start": 0, "end": 20, "score": 80},
        {"id": "b", "start": 60, "end": 80, "score": 70}]}
    expected = {"source_sha256": "same", "moments": [{"start": 0, "end": 20}, {"start": 30, "end": 50}]}
    result = module.evaluate(plan, expected)
    assert result["precision"] == .5
    assert result["moment_recall"] == .5
    assert result["missed_moments"] == [1]
    with pytest.raises(ValueError, match="source hash"):
        module.evaluate(plan, {**expected, "source_sha256": "other"})
