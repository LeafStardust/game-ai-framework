from types import SimpleNamespace

import games.balatro  # noqa: F401 - install production stack
import games.balatro.build_health_policy as policy
from games.balatro.actions import END_SHOP, REFRESH_SHOP, BalatroAction
from games.balatro.build_health import BuildHealth
from games.balatro.card import BalatroCard
from games.balatro.playbook.red_white.shop_policy import PlaybookBuildAwareShopArbiter
from games.balatro.shop_arbiter import BuildAwareShopArbiter


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

    def evaluate(self, state):
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
    return SimpleNamespace()


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


def test_early_devious_joker_fills_empty_survival_board_even_before_health_delta(monkeypatch):
    candidate = _joker("Devious Joker")
    state = _state(ante=1, jokers=(), slots=5)
    monkeypatch.setattr(
        policy,
        "_HEALTH",
        _HealthByRoster(
            {
                (): _health(survival=55, scaling=65),
                ("Devious Joker",): _health(survival=55, scaling=65),
            }
        ),
    )

    result = policy._health_aware_joker_decision(
        _acquisition_policy(),
        state,
        candidate,
        _decision(_option(money_after=3)),
    )

    assert result.action == "BUY"
    assert any("unfinished survival board" in note for note in result.rationale)


def test_demonstrated_two_pair_recruits_clever_joker(monkeypatch):
    base = _joker("Base")
    candidate = _joker("Clever Joker")
    state = _state(ante=4, jokers=(base,), slots=5)
    state.hand_play_counts = {"TWO_PAIR": 12, "PAIR": 4, "HIGH_CARD": 3}
    monkeypatch.setattr(
        policy,
        "_HEALTH",
        _HealthByRoster(
            {
                ("Base",): _health(survival=80, scaling=60),
                ("Base", "Clever Joker"): _health(survival=80, scaling=60),
            }
        ),
    )

    result = policy._health_aware_joker_decision(
        _acquisition_policy(),
        state,
        candidate,
        _decision(_option(money_after=15)),
    )

    assert result.action == "BUY"
    assert any("demonstrated TWO_PAIR" in note for note in result.rationale)


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


def test_full_roster_health_never_uses_ineligible_replacement(monkeypatch):
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


def test_projected_health_uses_only_projected_public_state(monkeypatch):
    class _Health:
        def evaluate(self, state):
            assert [joker.name for joker in state.jokers] == ["Candidate"]
            return _health(survival=80, scaling=60)

    state = _state(ante=4, jokers=(_joker("Base"),))
    monkeypatch.setattr(policy, "_HEALTH", _Health())

    result = policy._projected_health(state, (_joker("Candidate"),))

    assert result.survival == 80


def test_health_cache_invalidates_when_same_size_deck_structure_changes(monkeypatch):
    class _CountingHealth:
        def __init__(self):
            self.calls = 0

        def evaluate(self, state):
            del state
            self.calls += 1
            return _health(survival=80, scaling=60)

    health = _CountingHealth()
    monkeypatch.setattr(policy, "_HEALTH", health)
    owner = SimpleNamespace()
    state = _state(ante=4)
    state.owned_deck = [BalatroCard("A", "Spades"), BalatroCard("K", "Hearts")]

    policy._cached_health(owner, state)
    policy._cached_health(owner, state)
    assert health.calls == 1

    state.owned_deck = [BalatroCard("A", "Hearts"), BalatroCard("K", "Spades")]
    policy._cached_health(owner, state)

    assert health.calls == 2


def test_health_cache_invalidates_when_score_or_runner_history_changes(monkeypatch):
    class _CountingHealth:
        def __init__(self):
            self.calls = 0

        def evaluate(self, state):
            del state
            self.calls += 1
            return _health(survival=80, scaling=60)

    health = _CountingHealth()
    monkeypatch.setattr(policy, "_HEALTH", health)
    owner = SimpleNamespace()
    state = _state(ante=4)
    state.phase = "SELECTING_HAND"
    state.score = 0
    state.hand_play_counts = {"STRAIGHT": 0}

    policy._cached_health(owner, state)
    state.score = 250
    policy._cached_health(owner, state)
    state.hand_play_counts["STRAIGHT"] = 1
    policy._cached_health(owner, state)

    assert health.calls == 3


def test_active_blind_cache_tracks_remaining_draw_pile_not_owned_deck(monkeypatch):
    class _CountingHealth:
        def __init__(self):
            self.calls = 0

        def evaluate(self, state):
            del state
            self.calls += 1
            return _health(survival=80, scaling=60)

    health = _CountingHealth()
    monkeypatch.setattr(policy, "_HEALTH", health)
    owner = SimpleNamespace()
    state = _state(ante=4)
    state.phase = "SELECTING_HAND"
    state.owned_deck = [BalatroCard("A", "Spades"), BalatroCard("K", "Hearts")]
    state.deck = [BalatroCard("A", "Spades"), BalatroCard("K", "Hearts")]

    policy._cached_health(owner, state)
    state.deck = [BalatroCard("K", "Hearts")]
    policy._cached_health(owner, state)

    assert health.calls == 2


def test_production_build_aware_arbiter_reaches_patched_base_decide():
    assert "decide" not in PlaybookBuildAwareShopArbiter.__dict__
    assert PlaybookBuildAwareShopArbiter.decide is BuildAwareShopArbiter.decide
