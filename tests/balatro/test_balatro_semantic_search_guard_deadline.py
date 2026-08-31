from types import SimpleNamespace

from games.balatro.hand import PokerHand
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


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
    planner = LiveBlindClearPlanner()

    def fake_hand(state, action):
        calls.append(action)
        return PokerHand.PAIR

    monkeypatch.setattr(planner, "_cheap_hand", fake_hand)

    selected = planner._prefilter_plays(
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
    planner = LiveBlindClearPlanner()

    def fake_hand(state, action):
        calls.append(action)
        return PokerHand.PAIR

    monkeypatch.setattr(planner, "_cheap_hand", fake_hand)
    monkeypatch.setattr(
        planner,
        "_soft_deadline_reached",
        lambda soft_deadline, *, work_started: bool(work_started),
    )

    selected = planner._prefilter_plays(
        SimpleNamespace(),
        actions,
        limit=4,
        soft_deadline=1.0,
    )

    assert len(calls) == 1
    assert selected == [actions[0]]


def test_initial_root_play_ranking_does_not_call_expensive_projection_priority(monkeypatch):
    actions = [_action(str(rank)) for rank in range(2, 10)]
    state = SimpleNamespace()

    class Planner(LiveBlindClearPlanner):
        def _play_priority(self, state, action):
            raise AssertionError("initial-root ranking must stay projection-free")

        def _rank_actions_with_deadline(
            self,
            state,
            actions,
            *,
            priority,
            limit,
            soft_deadline=None,
        ):
            del soft_deadline
            return sorted(actions, key=lambda action: priority(state, action), reverse=True)[:limit]

    planner = Planner()
    monkeypatch.setattr(
        planner,
        "_cheap_play_key",
        lambda state, action: (int(action.cards[0].rank), 0, 0, 0),
    )

    selected = planner._rank_plays_with_short_reserve(
        state,
        actions,
        limit=3,
        soft_deadline=1.0,
    )

    assert [action.cards[0].rank for action in selected] == ["9", "8", "7"]
