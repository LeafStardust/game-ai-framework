from types import SimpleNamespace

import games.balatro.short_horizon_shop_planner as planner
from games.balatro.actions import BUY_JOKER, SELL_JOKER
from games.balatro.build_health import BuildHealth
from games.balatro.strategy import GOLD


def _health(total, survival, scaling, *, deficit=False):
    return BuildHealth(
        total=float(total),
        survival=float(survival),
        immediate=float(survival),
        scaling=float(scaling),
        coherence=50.0,
        runway=50.0,
        critical=False,
        scaling_deficit=bool(deficit),
        warnings=(),
        engines=(),
    )


class _Health:
    def evaluate(self, state, *, strategy_tracker=None):
        del strategy_tracker
        names = {
            planner._canonical_joker(joker)
            for joker in state.jokers
        }
        if {"bull", "bootstraps"} <= names:
            return _health(82, 90, 90)
        if {"hologram", "certificate"} <= names:
            return _health(76, 88, 75)
        return _health(55, 90, 25, deficit=True)


def _joker(name, *, cost=0, sell_cost=0, eternal=False):
    return SimpleNamespace(
        name=name,
        cost=cost,
        sell_cost=sell_cost,
        eternal=eternal,
        edition=None,
    )


def _state(*, jokers=(), shop=(), slots=5, money=50, ante=4):
    return SimpleNamespace(
        jokers=list(jokers),
        shop_jokers=list(shop),
        joker_slots=slots,
        money=money,
        ante=ante,
        phase="SHOP",
        blind_score=5000,
        hands_remaining=4,
        discards_remaining=3,
        hand_levels={},
        owned_deck=[],
        deck=[],
    )


def test_bull_bootstraps_pair_can_be_started_even_when_neither_single_buy_is_required(monkeypatch):
    monkeypatch.setattr(planner, "_HEALTH", _Health())
    bull = _joker("Bull", cost=6)
    bootstraps = _joker("Bootstraps", cost=7)
    state = _state(shop=(bull, bootstraps), money=50)
    arbiter = SimpleNamespace(_joker_policy_for_state=lambda state: SimpleNamespace(transition_planner=SimpleNamespace(evaluator=SimpleNamespace(strategy_tracker=None))))

    result = planner.recommend_bounded_shop_bundle(arbiter, state)

    assert result is not None
    assert result.bundle_id == "bull_bootstraps"
    assert result.action.name == BUY_JOKER
    assert result.action.target in (bull, bootstraps)
    assert any("re-observe" in note for note in result.rationale)


def test_hologram_certificate_bundle_is_recognized(monkeypatch):
    monkeypatch.setattr(planner, "_HEALTH", _Health())
    hologram = _joker("Hologram", cost=7)
    certificate = _joker("Certificate", cost=6)
    state = _state(shop=(hologram, certificate), money=40)
    arbiter = SimpleNamespace(_joker_policy_for_state=lambda state: SimpleNamespace(transition_planner=SimpleNamespace(evaluator=SimpleNamespace(strategy_tracker=None))))

    result = planner.recommend_bounded_shop_bundle(arbiter, state)

    assert result is not None
    assert result.bundle_id == "deck_growth:hologram+certificate"
    assert result.action.name == BUY_JOKER


def test_full_roster_bundle_sells_only_unprotected_filler(monkeypatch):
    monkeypatch.setattr(planner, "_HEALTH", _Health())
    core = _joker("Core", sell_cost=3)
    filler_a = _joker("Filler A", sell_cost=2)
    filler_b = _joker("Filler B", sell_cost=2)
    bull = _joker("Bull", cost=6)
    bootstraps = _joker("Bootstraps", cost=7)
    state = _state(
        jokers=(core, filler_a, filler_b),
        shop=(bull, bootstraps),
        slots=3,
        money=50,
    )

    class _Tracker:
        def evaluate_item(self, state, joker, *, kind):
            del state, kind
            return SimpleNamespace(
                active_alignment=joker is core,
                tier=GOLD if joker is core else None,
            )

    tracker = _Tracker()
    arbiter = SimpleNamespace(
        _joker_policy_for_state=lambda state: SimpleNamespace(
            transition_planner=SimpleNamespace(
                evaluator=SimpleNamespace(strategy_tracker=tracker)
            )
        )
    )

    result = planner.recommend_bounded_shop_bundle(arbiter, state)

    assert result is not None
    assert result.action.name == SELL_JOKER
    assert result.action.target in (1, 2)
    assert result.action.target != 0


def test_bundle_is_rejected_when_final_cash_breaks_reserve(monkeypatch):
    monkeypatch.setattr(planner, "_HEALTH", _Health())
    bull = _joker("Bull", cost=6)
    bootstraps = _joker("Bootstraps", cost=7)
    state = _state(shop=(bull, bootstraps), money=15, ante=4)
    arbiter = SimpleNamespace(_joker_policy_for_state=lambda state: SimpleNamespace(transition_planner=SimpleNamespace(evaluator=SimpleNamespace(strategy_tracker=None))))

    assert planner.recommend_bounded_shop_bundle(arbiter, state) is None
