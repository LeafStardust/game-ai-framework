from types import SimpleNamespace

import games.balatro  # noqa: F401 - install production stack
import games.balatro.build_health_policy as policy
from games.balatro.actions import END_SHOP, REFRESH_SHOP, BalatroAction
from games.balatro.build_health import BuildHealth


def _health(*, survival, scaling, immediate=80.0, deficit=False):
    return BuildHealth(
        total=60.0,
        survival=float(survival),
        immediate=float(immediate),
        scaling=float(scaling),
        coherence=50.0,
        runway=50.0,
        critical=survival < 20.0,
        scaling_deficit=bool(deficit),
        warnings=(),
        engines=(),
    )


class _HealthByRoster:
    def __init__(self, mapping):
        self.mapping = mapping

    def evaluate(self, state, *, strategy_tracker=None):
        del strategy_tracker
        tokens = tuple(getattr(joker, "name", "") for joker in state.jokers)
        return self.mapping[tokens]


def _state(*, ante, money=20, jokers=(), slots=5):
    return SimpleNamespace(
        ante=ante,
        phase="SHOP",
        money=money,
        blind_score=1000,
        hands_remaining=4,
        discards_remaining=3,
        jokers=list(jokers),
        joker_slots=slots,
        hand_levels={},
        owned_deck=[],
        deck=[],
        round=1,
    )


def _decision(option, *, action="HOLD", reserve=5):
    return SimpleNamespace(
        action=action,
        selected=None,
        options=(option,),
        thresholds=SimpleNamespace(reserve_target=reserve),
        rationale=(),
    )


def _option(*, eligible=True, money_after=10, advantage=1.0, index=None):
    return SimpleNamespace(
        eligible=eligible,
        total_advantage=advantage,
        economics=SimpleNamespace(money_after=money_after),
        replace_index=index,
        rationale=(),
    )


def _joker(name):
    return SimpleNamespace(name=name, x_mult=0.0, mult=0.0, chips=0.0, eternal=False)


def _acquisition_policy():
    return SimpleNamespace(
        transition_planner=SimpleNamespace(
            evaluator=SimpleNamespace(strategy_tracker=None)
        )
    )


def test_early_hold_becomes_buy_only_when_projected_survival_materially_improves(monkeypatch):
    base = _joker("Base")
    candidate = _joker("Scorer")
    state = _state(ante=1, jokers=(base,), slots=5)
    monkeypatch.setattr(
        policy,
        "_HEALTH",
        _HealthByRoster(
            {
                ("Base",): _health(survival=55, scaling=65),
                ("Base", "Scorer"): _health(survival=78, scaling=65),
            }
        ),
    )

    result = policy._health_aware_joker_decision(
        _acquisition_policy(),
        state,
        candidate,
        _decision(_option(money_after=8)),
    )

    assert result.action == "BUY"
    assert result.selected is not None
    assert any("survival adequacy" in note for note in result.rationale)


def test_early_positive_piece_that_does_not_fix_survival_stays_hold(monkeypatch):
    base = _joker("Base")
    candidate = _joker("TokenChips")
    state = _state(ante=1, jokers=(base,), slots=5)
    monkeypatch.setattr(
        policy,
        "_HEALTH",
        _HealthByRoster(
            {
                ("Base",): _health(survival=55, scaling=65),
                ("Base", "TokenChips"): _health(survival=58, scaling=65),
            }
        ),
    )

    result = policy._health_aware_joker_decision(
        _acquisition_policy(),
        state,
        candidate,
        _decision(_option(money_after=8)),
    )

    assert result.action == "HOLD"


def test_scaling_fix_cannot_trade_away_material_survival(monkeypatch):
    base = _joker("Base")
    candidate = _joker("Scaler")
    state = _state(ante=4, jokers=(base,), slots=5)
    monkeypatch.setattr(
        policy,
        "_HEALTH",
        _HealthByRoster(
            {
                ("Base",): _health(survival=90, scaling=30, deficit=True),
                ("Base", "Scaler"): _health(survival=80, scaling=70, deficit=False),
            }
        ),
    )

    result = policy._health_aware_joker_decision(
        _acquisition_policy(),
        state,
        candidate,
        _decision(_option(money_after=15), reserve=5),
    )

    assert result.action == "HOLD"


def test_full_roster_health_never_uses_ineligible_committed_replacement(monkeypatch):
    core = _joker("Core")
    candidate = _joker("Scaler")
    state = _state(ante=4, jokers=(core,), slots=1)
    monkeypatch.setattr(
        policy,
        "_HEALTH",
        _HealthByRoster(
            {
                ("Core",): _health(survival=90, scaling=25, deficit=True),
                ("Scaler",): _health(survival=90, scaling=80, deficit=False),
            }
        ),
    )

    result = policy._health_aware_joker_decision(
        _acquisition_policy(),
        state,
        candidate,
        _decision(_option(eligible=False, money_after=15, advantage=10.0, index=0)),
    )

    assert result.action == "HOLD"


def test_build_health_reroll_is_bounded_to_one_per_shop(monkeypatch):
    state = _state(ante=4, money=30)
    arbiter = SimpleNamespace(
        _joker_policy_for_state=lambda _state: _acquisition_policy(),
    )
    monkeypatch.setattr(
        policy,
        "_HEALTH",
        _HealthByRoster({(): _health(survival=90, scaling=25, deficit=True)}),
    )
    original = SimpleNamespace(
        action=BalatroAction(END_SHOP),
        source="END_SHOP",
        normalized_gain=0.0,
        rationale=(),
    )

    first = policy._health_reroll_decision(arbiter, state, original, 5)
    second = policy._health_reroll_decision(arbiter, state, original, 5)

    assert first.action.name == REFRESH_SHOP
    assert first.source == "BUILD_HEALTH_REROLL"
    assert second.action.name == END_SHOP


def test_projected_health_uses_isolated_strategy_tracker(monkeypatch):
    class _Tracker:
        def __init__(self):
            self.calls = 0

    class _MutatingHealth:
        def evaluate(self, state, *, strategy_tracker=None):
            del state
            strategy_tracker.calls += 1
            return _health(survival=80, scaling=60)

    tracker = _Tracker()
    state = _state(ante=4, jokers=(_joker("Base"),))
    monkeypatch.setattr(policy, "_HEALTH", _MutatingHealth())

    result = policy._projected_health(state, (_joker("Candidate"),), tracker)

    assert result.survival == 80
    assert tracker.calls == 0
