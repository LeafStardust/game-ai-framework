from types import SimpleNamespace

from games.balatro.actions import SELECT_PACK_CARD, BalatroAction
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planet_pack_fallback_policy import install_planet_pack_fallback_policy


def _planet(label: str, index: int) -> BalatroAction:
    choice = LivePackChoice(area_index=index, address=100 + index, data={"ability_set": "PLANET", "label": label})
    return BalatroAction(SELECT_PACK_CARD, target=choice)


def _state(*, levels=None, plays=None):
    return SimpleNamespace(phase="PLANET_PACK", hand_levels=levels or {}, hand_play_counts=plays or {})


def _policy_with_scores(scores):
    install_planet_pack_fallback_policy()
    policy = BalatroPackPolicy()
    policy.score_action = lambda state, action: PackActionScore(action, scores[action.target.label], ("synthetic base score",))
    return policy


def test_planet_pack_does_not_force_practical_fallback_without_direction():
    actions = [_planet("Uranus", 0), _planet("Mercury", 1), _planet("Pluto", 2)]
    ranked = _policy_with_scores({"Uranus": 5.0, "Mercury": 4.0, "Pluto": 1.0}).rank_actions(_state(), actions)
    assert ranked[0].action.target.label == "Uranus"
    assert "Planet pack full-pool selection authority" not in ranked[0].notes


def test_planet_pack_keeps_base_ranking_for_off_path_planets():
    actions = [_planet("Jupiter", 0), _planet("Mars", 1), _planet("Neptune", 2)]
    ranked = _policy_with_scores({"Jupiter": 1.0, "Mars": 9.0, "Neptune": 10.0}).rank_actions(_state(), actions)
    assert ranked[0].action.target.label == "Neptune"


def test_planet_pack_keeps_materially_developed_current_hand_over_practical_fallback():
    actions = [_planet("Uranus", 0), _planet("Pluto", 1)]
    ranked = _policy_with_scores({"Uranus": 5.0, "Pluto": 1.0}).rank_actions(_state(levels={"TWO_PAIR": 3}, plays={"TWO_PAIR": 9}), actions)
    assert ranked[0].action.target.label == "Uranus"


def test_planet_pack_observed_hand_overrides_practical_fallback(monkeypatch):
    import games.balatro.planet_pack_fallback_policy as module
    monkeypatch.setattr(module, "_observed_hand_goals", lambda state: {"PAIR"})
    actions = [_planet("Neptune", 0), _planet("Mercury", 1)]
    ranked = _policy_with_scores({"Neptune": 10.0, "Mercury": 1.0}).rank_actions(_state(), actions)
    assert ranked[0].action.target.label == "Mercury"


def test_planet_pack_actual_two_pair_play_beats_zero_play_four_kind_level():
    actions = [_planet("Mars", 0), _planet("Uranus", 1)]
    ranked = _policy_with_scores({"Mars": 10.0, "Uranus": 1.0}).rank_actions(_state(levels={"FOUR_OF_A_KIND": 3, "TWO_PAIR": 1}, plays={"FOUR_OF_A_KIND": 0, "TWO_PAIR": 16}), actions)
    assert ranked[0].action.target.label == "Uranus"


def test_planet_pack_zero_play_levels_do_not_manufacture_relevance():
    actions = [_planet("Mars", 0), _planet("Mercury", 1)]
    ranked = _policy_with_scores({"Mars": 10.0, "Mercury": 1.0}).rank_actions(_state(levels={"FOUR_OF_A_KIND": 3}, plays={"FOUR_OF_A_KIND": 0}), actions)
    assert ranked[0].action.target.label == "Mars"


def test_planet_pack_one_incidental_play_does_not_trigger_forced_promotion():
    actions = [_planet("Neptune", 0), _planet("Mercury", 1)]
    ranked = _policy_with_scores({"Neptune": 10.0, "Mercury": 1.0}).rank_actions(_state(levels={"STRAIGHT_FLUSH": 1, "PAIR": 1}, plays={"STRAIGHT_FLUSH": 1, "PAIR": 0}), actions)
    assert ranked[0].action.target.label == "Neptune"


def test_planet_pack_does_not_promote_vetoed_relevant_planet(monkeypatch):
    import games.balatro.planet_pack_fallback_policy as module
    monkeypatch.setattr(module, "_observed_hand_goals", lambda state: {"PAIR"})
    actions = [_planet("Mercury", 0), _planet("Mars", 1)]
    ranked = _policy_with_scores({"Mercury": -1.0, "Mars": 0.2}).rank_actions(_state(), actions)
    assert ranked[0].action.target.label == "Mars"
    assert "Planet pack full-pool selection authority" not in ranked[0].notes


def test_planet_pack_sustained_exotic_play_can_beat_practical_fallback():
    actions = [_planet("Neptune", 0), _planet("Mercury", 1)]
    ranked = _policy_with_scores({"Neptune": 1.0, "Mercury": 10.0}).rank_actions(_state(levels={"STRAIGHT_FLUSH": 1, "PAIR": 1}, plays={"STRAIGHT_FLUSH": 3, "PAIR": 0}), actions)
    assert ranked[0].action.target.label == "Neptune"
