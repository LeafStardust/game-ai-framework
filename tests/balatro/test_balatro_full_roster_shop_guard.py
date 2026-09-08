from types import SimpleNamespace

from games.balatro.actions import BUY_JOKER, SELL_JOKER, BalatroAction
from games.balatro.full_roster_shop_guard import authoritative_joker_capacity
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)


def _snapshot(*, count: int, limit: int) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "jokers": {
                "cards": [{"live_id": index + 1} for index in range(count)],
                "count": count,
                "limit": limit,
            }
        },
    )


class _Generator:
    def generate_actions(self, state):
        return []


class _Arbiter:
    def __init__(self, candidate, replacement):
        self.candidate = candidate
        self.replacement = replacement

    def decide(self, state, visible_actions, *, reroll_cost):
        return SimpleNamespace(
            action=BalatroAction(BUY_JOKER, target=self.candidate),
            source="JOKER_BUY",
            total=3.0,
            reroll=None,
            rationale=("upstream attempted direct buy",),
        )

    def _best_joker_decision(self, state):
        return self.replacement


class _Terms:
    cost = 5
    free_rerolls = 0


def _runner(candidate, replacement):
    runner = object.__new__(LiveMemoryInjectedSingleStepRunner)
    runner.shop_generator = _Generator()
    runner.shop_arbiter = _Arbiter(candidate, replacement)
    runner.reroll_terms_reader = lambda: _Terms()
    return runner


def test_authoritative_capacity_uses_raw_owned_area_not_modeled_roster():
    assert authoritative_joker_capacity(_snapshot(count=6, limit=6)) == (6, 6)
    assert authoritative_joker_capacity(_snapshot(count=5, limit=6)) == (5, 6)


def test_full_roster_direct_buy_is_normalized_to_d2_sell_checkpoint():
    candidate = SimpleNamespace(edition=None, label="Burnt Joker")
    selected = SimpleNamespace(replace_index=1, replace_joker="ZanyJoker")
    replacement = SimpleNamespace(
        action=BalatroAction(SELL_JOKER, target=1),
        source="JOKER_REPLACE_SELL",
        decision=SimpleNamespace(selected=selected),
    )
    runner = _runner(candidate, replacement)

    action, notes = LiveMemoryInjectedSingleStepRunner._recommend_shop(
        runner,
        SimpleNamespace(),
        _snapshot(count=6, limit=6),
    )

    assert action.name == SELL_JOKER
    assert action.target == 1
    assert any("blocked direct Joker BUY" in note for note in notes)
    assert any("fresh settled SHOP observation" in note for note in notes)


def test_nonfull_roster_preserves_admitted_direct_buy():
    candidate = SimpleNamespace(edition=None, label="Burnt Joker")
    runner = _runner(candidate, replacement=None)

    action, notes = LiveMemoryInjectedSingleStepRunner._recommend_shop(
        runner,
        SimpleNamespace(),
        _snapshot(count=5, limit=6),
    )

    assert action.name == BUY_JOKER
    assert action.target is candidate
    assert not any("full-roster guard" in note for note in notes)


def test_negative_joker_remains_buyable_at_full_authoritative_capacity():
    candidate = SimpleNamespace(edition="Negative", label="Negative Joker")
    runner = _runner(candidate, replacement=None)

    action, _ = LiveMemoryInjectedSingleStepRunner._recommend_shop(
        runner,
        SimpleNamespace(),
        _snapshot(count=6, limit=6),
    )

    assert action.name == BUY_JOKER
