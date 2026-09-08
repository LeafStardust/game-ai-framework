from types import SimpleNamespace

import games.balatro.d1_candidate_deadline_policy as module


def test_root_candidate_ranking_returns_scored_partial_beam_at_soft_deadline(monkeypatch):
    clock = {"now": 0.0}

    def fake_time():
        return clock["now"]

    def priority(state, action):
        clock["now"] += 1.0
        return float(action)

    monkeypatch.setattr(module, "perf_counter", fake_time)
    planner = SimpleNamespace(deadline=100.0)

    ranked = module._rank_with_deadline(
        planner,
        object(),
        [1, 2, 3, 4],
        key=priority,
        limit=4,
        stage="synthetic root ranking",
        soft_deadline=0.75,
    )

    assert ranked == [1]
    assert clock["now"] == 1.0


def test_child_candidate_ranking_remains_exhaustive_without_soft_deadline(monkeypatch):
    clock = {"now": 0.0}

    def fake_time():
        return clock["now"]

    def priority(state, action):
        clock["now"] += 0.1
        return float(action)

    monkeypatch.setattr(module, "perf_counter", fake_time)
    planner = SimpleNamespace(deadline=100.0)

    ranked = module._rank_with_deadline(
        planner,
        object(),
        [1, 2, 3, 4],
        key=priority,
        limit=2,
        stage="synthetic child ranking",
    )

    assert ranked == [4, 3]
    assert clock["now"] == 0.4
