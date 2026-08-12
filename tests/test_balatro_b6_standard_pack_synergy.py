from games.balatro.actions import BalatroAction, SELECT_PACK_CARD
from games.balatro.build import ContextualPlayingCardSynergyEvaluator
from games.balatro.card import BalatroCard
from games.balatro.jokers.baron import BaronJoker
from games.balatro.live.pack import LivePackChoice
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


def _state(*, baron: bool = False) -> BalatroState:
    state = BalatroState()
    state.phase = "STANDARD_PACK"
    state.joker_slots = 5
    state.jokers = [BaronJoker()] if baron else []
    state.deck = [BalatroCard("Q", "Hearts") for _ in range(8)]
    return state


def _choice(index: int, rank: str, *, suit: str = "Hearts") -> LivePackChoice:
    return LivePackChoice(
        area_index=index,
        address=100 + index,
        data={
            "area_index": index,
            "ability_set": "PLAYING_CARD",
            "live_id": index + 1,
            "value": {"rank": rank, "suit": suit},
            "modifier": {},
        },
    )


def test_plain_build_adds_no_contextual_value_to_vanilla_card():
    value = ContextualPlayingCardSynergyEvaluator().evaluate(
        _state(),
        rank="K",
        suit="Hearts",
    )

    assert value.total_gain == 0.0
    assert value.contributions == ()


def test_baron_build_values_visible_king_as_held_king_source():
    value = ContextualPlayingCardSynergyEvaluator().evaluate(
        _state(baron=True),
        rank="King",
        suit="Hearts",
    )

    assert value.total_gain > 0.0
    assert "held:rank:K" in value.prospective_features
    assert any(
        contribution.feature == "held:rank:K"
        and contribution.source == "BaronJoker"
        for contribution in value.contributions
    )


def test_baron_context_can_flip_standard_pack_ace_vs_king_ordering():
    ace = BalatroAction(SELECT_PACK_CARD, target=_choice(0, "A"))
    king = BalatroAction(SELECT_PACK_CARD, target=_choice(1, "K"))
    policy = BalatroPackPolicy(skip_bias=0.0)

    plain = policy.rank_actions(_state(), [ace, king])
    baron = policy.rank_actions(_state(baron=True), [ace, king])

    assert plain[0].action.target.data["value"]["rank"] == "A"
    assert baron[0].action.target.data["value"]["rank"] == "K"


def test_standard_pack_score_explains_b6_build_gain():
    action = BalatroAction(SELECT_PACK_CARD, target=_choice(0, "K"))

    score = BalatroPackPolicy(skip_bias=0.0).score_action(
        _state(baron=True),
        action,
    )

    assert score.total > BalatroPackPolicy.RANK_VALUE["K"]
    assert any(note.startswith("B6 playing-card build gain=") for note in score.notes)
    assert any("held:rank:K" in note and "BaronJoker" in note for note in score.notes)
