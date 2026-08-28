from types import SimpleNamespace

from games.balatro.hand import PokerHand
import games.balatro.semantic_search_guard_policy as guard


class _Planner:
    def _check_deadline(self):
        return None


def _action(rank):
    card = SimpleNamespace(
        rank=rank,
        enhancement=None,
        edition=None,
        seal=None,
    )
    return SimpleNamespace(cards=(card,))


def test_play_prefilter_classifies_each_candidate_once(monkeypatch):
    actions = [_action(str(rank)) for rank in range(2, 10)]
    calls = []

    def fake_hand(state, action):
        calls.append(action)
        return PokerHand.PAIR

    monkeypatch.setattr(guard, "_cheap_hand", fake_hand)

    selected = guard._prefilter_plays(
        _Planner(),
        SimpleNamespace(),
        actions,
        limit=4,
        soft_deadline=None,
    )

    assert len(selected) <= 4
    assert len(calls) == len(actions)
    assert {id(action) for action in calls} == {id(action) for action in actions}


def test_play_prefilter_stops_when_root_soft_deadline_expires(monkeypatch):
    actions = [_action(str(rank)) for rank in range(2, 10)]
    calls = []

    def fake_hand(state, action):
        calls.append(action)
        return PokerHand.PAIR

    monkeypatch.setattr(guard, "_cheap_hand", fake_hand)
    monkeypatch.setattr(
        guard,
        "_soft_deadline_reached",
        lambda soft_deadline, *, work_started: bool(work_started),
    )

    selected = guard._prefilter_plays(
        _Planner(),
        SimpleNamespace(),
        actions,
        limit=4,
        soft_deadline=1.0,
    )

    assert len(calls) == 1
    assert selected == [actions[0]]
