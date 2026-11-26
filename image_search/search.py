"""Cosine search, per-object aggregation and the match / ambiguous / no_match decision."""
import numpy as np

# Frozen on 26 Nov 2026: tuned on the val split of data/eval/underwater_queries.csv only
# (eval/underwater/calibrate.py, balanced accuracy, ambiguous = half credit). EmbeddingGemma 2,
# budget 280, no colour correction. Do not retune on test results.
TAU = 0.875   # minimum top-1 object score to accept a match
DELTA = 0.04  # minimum gap between the top-2 objects to call it unambiguous


def rank_objects(query: np.ndarray, emb: np.ndarray, rows: list) -> list:
    """[(object_id, score, best_row)] sorted by score; score = max cosine over the object's views."""
    scores = emb @ query  # both L2-normalised
    best = {}
    for i, s in enumerate(scores):
        oid = rows[i]["object_id"]
        if oid not in best or s > best[oid][0]:
            best[oid] = (float(s), i)
    return sorted(((oid, s, i) for oid, (s, i) in best.items()), key=lambda t: -t[1])


def decide(ranked: list, tau: float = TAU, delta: float = DELTA) -> tuple:
    """Return (decision, object_ids to pass on)."""
    if not ranked or ranked[0][1] < tau:
        return "no_match", []
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < delta:
        return "ambiguous", [ranked[0][0], ranked[1][0]]
    return "match", [ranked[0][0]]


if __name__ == "__main__":  # self-check of the decision rule on hand-made scores
    assert decide([]) == ("no_match", [])
    assert decide([("a", 0.4, 0), ("b", 0.1, 1)], 0.8, 0.03) == ("no_match", [])
    assert decide([("a", 0.8, 0), ("b", 0.79, 1)], 0.8, 0.03) == ("ambiguous", ["a", "b"])
    assert decide([("a", 0.8, 0), ("b", 0.6, 1)], 0.8, 0.03) == ("match", ["a"])
    emb = np.eye(3, dtype=np.float32)
    rows = [{"object_id": "a"}, {"object_id": "a"}, {"object_id": "b"}]
    assert [o for o, _, _ in rank_objects(np.array([0, 1, 0], np.float32), emb, rows)] == ["a", "b"]
    print("search.py self-check ok")
