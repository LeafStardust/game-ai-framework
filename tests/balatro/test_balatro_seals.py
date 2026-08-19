from games.balatro.card import BalatroCard
from games.balatro.environment import BalatroEnvironment
from games.balatro.hand import PokerHand
from games.balatro.scoring import BalatroScorer


def test_red_seal_retriggers_played_card_modifier():

    scorer = BalatroScorer()

    score = scorer.score(
        PokerHand.HIGH_CARD,
        cards=[
            BalatroCard(
                "A",
                "Hearts",
                enhancement="Mult",
                seal="Red"
            )
        ]
    )

    assert score.mult == 9


def test_gold_seal_gives_money_at_end_of_round():

    environment = BalatroEnvironment()
    card = BalatroCard(
        "A",
        "Hearts",
        seal="Gold"
    )
    environment.state.hand = [card]
    environment.state.money = 5

    environment._resolve_end_round_seals(
        environment.state
    )

    assert environment.state.money == 8


def test_purple_seal_creates_tarot_when_discarded():

    environment = BalatroEnvironment()
    card = BalatroCard(
        "A",
        "Hearts",
        seal="Purple"
    )
    environment.state.hand = [card]

    environment._trigger_discard_seals(
        environment.state,
        [card]
    )

    assert len(environment.state.consumables) == 1
    assert environment.state.consumables[0].category == "TAROT"


def test_blue_seal_creates_planet_for_last_played_hand():

    environment = BalatroEnvironment()
    card = BalatroCard(
        "A",
        "Hearts",
        seal="Blue"
    )
    environment.state.hand = [card]
    environment.state.last_played_hand = "PAIR"

    environment._resolve_end_round_seals(
        environment.state
    )

    assert len(environment.state.consumables) == 1
    assert environment.state.consumables[0].category == "PLANET"
    assert environment.state.consumables[0].hand_type == "PAIR"
