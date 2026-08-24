from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, BalatroAction
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planet_pack_fallback_policy import install_planet_pack_fallback_policy


def _planet(label: str, index: int) -> BalatroAction:
    choice = LivePackChoice(
        area_index=index,
        address=100 + index,
        data={"ability_set": "PLANET", "label": label},
    )
    return BalatroAction(SELECT_PACK_CARD, target=choice)


def _state(*, levels=None, plays=None):
    return SimpleNamespace(
        phase="PLANET_PACK",
        hand_levels=levels or {},
        hand_play_counts=plays or {},
    )


def _policy_with_scores(scores):
    install_planet_pack_fallback_policy()
    policy = BalatroPackPolicy()
    policy.score_action = lambda state, action: PackActionScore(
        action,
        scores[action.target.label],
        ("synthetic base score",),
    )
    return policy


def test_planet_pack_uses_full_pool_generic_upgrade_when_no_hand_is_good(monkeypatch):
    import games.balatro.planet_pack_fallback_policy as module

    monkeypatch.setattr(module, "_plan_hand_goals", lambda state: set())
    actions = [_planet("Uranus", 0), _planet("Mercury", 1), _planet("Pluto", 2)]
    policy = _policy_with_scores({"Uranus": 5.0, "Mercury": 4.0, "Pluto": 1.0})

    ranked = policy.rank_actions(_state(), actions)

    assert ranked[0].action.target.label == "Uranus"
    assert "Planet pack full-pool selection authority" in ranked[0].notes


def test_planet_pack_generic_priority_covers_nonlegacy_planets(monkeypatch):
    import games.balatro.planet_pack_fallback_policy as module

    monkeypatch.setattr(module, "_plan_hand_goals", lambda state: set())
    actions = [_planet("Venus", 0), _planet("Uranus", 1), _planet("Mercury", 2)]
    policy = _policy_with_scores({"Venus": 6.0, "Uranus": 7.0, "Mercury": 1.0})

    ranked = policy.rank_actions(_state(), actions)

    assert ranked[0].action.target.label == "Venus"


def test_planet_pack_keeps_materially_developed_current_hand_over_generic_priority(monkeypatch):
    import games.balatro.planet_pack_fallback_policy as module

    monkeypatch.setattr(module, "_plan_hand_goals", lambda state: set())
    actions = [_planet("Uranus", 0), _planet("Pluto", 1)]
    policy = _policy_with_scores({"Uranus": 5.0, "Pluto": 1.0})

    ranked = policy.rank_actions(
        _state(levels={"TWO_PAIR": 3}, plays={"TWO_PAIR": 9}),
        actions,
    )

    assert ranked[0].action.target.label == "Uranus"


def test_planet_pack_strategy_hand_overrides_generic_upgrade(monkeypatch):
    import games.balatro.planet_pack_fallback_policy as module

    monkeypatch.setattr(module, "_plan_hand_goals", lambda state: {"PAIR"})
    actions = [_planet("Neptune", 0), _planet("Mercury", 1)]
    policy = _policy_with_scores({"Neptune": 10.0, "Mercury": 1.0})

    ranked = policy.rank_actions(_state(), actions)

    assert ranked[0].action.target.label == "Mercury"
