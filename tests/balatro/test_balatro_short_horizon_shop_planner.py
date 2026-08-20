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
        names = {planner._canonical_joker(joker) for joker in state.jokers}
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
        score=0,
        blind_score=5000,
        hands_remaining=4,
        discards_remaining=3,
        hand_levels={},
        hand_play_counts={},
        owned_deck=[],
        deck=[],
    )


def _arbiter(tracker=None):
    return SimpleNamespace(
        _joker_policy_for_state=lambda state: SimpleNamespace(
            transition_planner=SimpleNamespace(
                evaluator=SimpleNamespace(strategy_tracker=tracker)
            )
        )
    )


def test_bull_bootstraps_pair_can_be_started_even_when_neither_single_buy_is_required(monkeypatch):
    monkeypatch.setattr(planner, "_HEALTH", _Health())
    bull = _joker("Bull", cost=6)
    bootstraps = _joker("Bootstraps", cost=7)
    state = _state(shop=(bull, bootstraps), money=50)

    result = planner.recommend_bounded_shop_bundle(_arbiter(), state)

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

    result = planner.recommend_bounded_shop_bundle(_arbiter(), state)

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
                active_alignment=joker.name == "Core",
                tier=GOLD if joker.name == "Core" else None,
            )

    result = planner.recommend_bounded_shop_bundle(_arbiter(_Tracker()), state)

    assert result is not None
    assert result.action.name == SELL_JOKER
    assert result.action.target in (1, 2)
    assert result.action.target != 0


def test_bundle_is_rejected_when_final_cash_breaks_reserve(monkeypatch):
    monkeypatch.setattr(planner, "_HEALTH", _Health())
    bull = _joker("Bull", cost=6)
    bootstraps = _joker("Bootstraps", cost=7)
    state = _state(shop=(bull, bootstraps), money=15, ante=4)

    assert planner.recommend_bounded_shop_bundle(_arbiter(), state) is None


def test_bundle_protection_uses_isolated_strategy_tracker():
    class _Tracker:
        def __init__(self):
            self.calls = 0

        def evaluate_item(self, state, joker, *, kind):
            del state, joker, kind
            self.calls += 1
            return SimpleNamespace(active_alignment=True, tier=GOLD)

    tracker = _Tracker()
    state = _state(jokers=(_joker("Core"),))

    protected = planner._protected_indices(state, tracker)

    assert protected == {0}
    assert tracker.calls == 0


def test_bundle_protection_fails_closed_when_tracker_cannot_be_copied():
    class _UncopyableTracker:
        def __deepcopy__(self, memo):
            del memo
            raise TypeError("not copyable")

    state = _state(jokers=(_joker("One"), _joker("Two")))

    assert planner._protected_indices(state, _UncopyableTracker()) == {0, 1}


def test_duplicate_visible_semantic_offers_are_preserved():
    expensive = _joker("Certificate Joker", cost=9)
    cheap = _joker("Certificate Joker", cost=4)

    offers = planner._visible_offers((expensive, cheap))

    assert offers["certificate"] == (expensive, cheap)


def test_bundle_planner_prefers_better_economics_between_duplicate_offers(monkeypatch):
    monkeypatch.setattr(planner, "_HEALTH", _Health())
    hologram = _joker("Hologram")
    expensive = _joker("Certificate Joker", cost=9)
    cheap = _joker("Certificate Joker", cost=4)
    state = _state(
        jokers=(hologram,),
        shop=(expensive, cheap),
        slots=5,
        money=30,
    )

    result = planner.recommend_bounded_shop_bundle(_arbiter(), state)

    assert result is not None
    assert result.action.name == BUY_JOKER
    assert result.action.target is cheap


def test_bundle_rejects_good_final_pair_when_every_first_buy_harms_survival(monkeypatch):
    class _UnsafeFirstBuyHealth:
        def evaluate(self, state, *, strategy_tracker=None):
            del strategy_tracker
            names = {planner._canonical_joker(joker) for joker in state.jokers}
            if {"bull", "bootstraps"} <= names:
                return _health(80, 90, 90)
            if names & {"bull", "bootstraps"}:
                return _health(45, 70, 35, deficit=True)
            return _health(55, 90, 25, deficit=True)

    monkeypatch.setattr(planner, "_HEALTH", _UnsafeFirstBuyHealth())
    state = _state(
        shop=(_joker("Bull", cost=6), _joker("Bootstraps", cost=7)),
        slots=5,
        money=50,
    )

    assert planner.recommend_bounded_shop_bundle(_arbiter(), state) is None


def test_bundle_rejects_good_final_pair_when_required_presale_harms_survival(monkeypatch):
    class _UnsafeSaleHealth:
        def evaluate(self, state, *, strategy_tracker=None):
            del strategy_tracker
            names = {planner._canonical_joker(joker) for joker in state.jokers}
            if {"bull", "bootstraps"} <= names:
                return _health(80, 90, 90)
            if "filler" not in names:
                return _health(40, 65, 30, deficit=True)
            return _health(55, 90, 25, deficit=True)

    monkeypatch.setattr(planner, "_HEALTH", _UnsafeSaleHealth())
    filler = _joker("Filler", sell_cost=3)
    state = _state(
        jokers=(filler,),
        shop=(_joker("Bull", cost=6), _joker("Bootstraps", cost=7)),
        slots=2,
        money=50,
    )

    assert planner.recommend_bounded_shop_bundle(_arbiter(), state) is None
