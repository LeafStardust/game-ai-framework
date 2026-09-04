from games.balatro.card import BalatroCard
from games.balatro.env.state import EnvStateFrame
from games.balatro.state import BalatroState


def test_env_r2_face_down_hand_identity_is_masked_without_mutating_internal_state():
    state = BalatroState()
    hidden = BalatroCard(
        "A",
        "Spades",
        enhancement="Gold",
        edition="Foil",
        seal="Red",
        live_id=117,
        debuffed=True,
        permanent_bonus=9,
        forced_selection=True,
        face_down=True,
        original_suit_nominal=0.04,
    )
    visible = BalatroCard("K", "Hearts", live_id=118)
    state.hand = [hidden, visible]

    observation = EnvStateFrame(state=state).observation()

    assert observation is not state
    assert observation.hand[0] == BalatroCard(
        "?",
        "?",
        live_id=None,
        forced_selection=True,
        face_down=True,
    )
    assert observation.hand[1] == visible
    assert observation.hand[1] is not visible

    assert state.hand[0] is hidden
    assert state.hand[0].rank == "A"
    assert state.hand[0].suit == "Spades"
    assert state.hand[0].live_id == 117
    assert state.hand[0].enhancement == "Gold"
    assert state.hand[0].edition == "Foil"
    assert state.hand[0].seal == "Red"
    assert state.hand[0].debuff is True
    assert state.hand[0].permanent_bonus == 9
    assert state.hand[0].original_suit_nominal == 0.04


def test_env_r2_face_up_observation_preserves_historical_copy_behavior():
    state = BalatroState()
    state.hand = [BalatroCard("Q", "Diamonds", live_id=22)]
    state.deck = [BalatroCard("2", "Clubs", live_id=23)]

    observation = EnvStateFrame(state=state).observation()

    assert observation == state
    assert observation is not state
    assert observation.hand[0] is not state.hand[0]
    assert observation.deck[0] is not state.deck[0]
