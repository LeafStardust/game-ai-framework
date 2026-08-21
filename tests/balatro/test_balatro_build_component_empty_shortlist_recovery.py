from types import SimpleNamespace

from games.balatro.build_component_roles import BuildComponentRole, BuildComponentRoleClassifier
from games.balatro.strategy import NEUTRAL, SILVER


class GreenJoker:
    name = "Green Joker"
    public_state = {"mult": 12}


class _Definition:
    def relationship_for(self, item, *, kind: str):
        return SILVER if isinstance(item, GreenJoker) and kind == "JOKER" else NEUTRAL


class _Tracker:
    definitions = {"no_discard_green": _Definition()}

    def observe(self, state):
        return SimpleNamespace(
            dominant_strategy_id="no_discard_green",
            relevant_strategy_ids=("pair",),
            shortlist_strategy_ids=(),
        )

    def evaluate_item(self, state, item, *, kind: str):
        return SimpleNamespace(
            strategy_id=None,
            tier=None,
            active_alignment=False,
        )


def test_empty_exposed_shortlist_falls_back_to_dominant_and_relevant_ids():
    state = SimpleNamespace(
        jokers=[GreenJoker()],
        ante=4,
        blind_score=7500,
        hands_remaining=4,
        phase="SHOP",
        owned_deck=[],
        deck=[],
        hand_levels={},
    )

    component = BuildComponentRoleClassifier().classify(
        state,
        strategy_tracker=_Tracker(),
    )[0]

    assert component.role == BuildComponentRole.ENGINE
    assert component.strategy_id == "no_discard_green"
    assert component.tier == SILVER
    assert any("recovered directly" in note for note in component.rationale)
