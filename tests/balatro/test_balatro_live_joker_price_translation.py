from games.balatro.live.joker_factory import LiveJokerFactory


def test_live_joker_factory_normalizes_exact_integer_float_prices():
    joker = LiveJokerFactory().create(
        {
            "center": "j_juggler",
            "label": "Juggler",
            "base_cost": 4.0,
            "cost": 4.0,
            "sell_cost": 2.0,
        }
    )

    assert joker is not None
    assert type(joker.base_cost) is int
    assert type(joker.cost) is int
    assert type(joker.sell_cost) is int
    assert (joker.base_cost, joker.cost, joker.sell_cost) == (4, 4, 2)


def test_live_joker_factory_does_not_round_nonintegral_price_metadata():
    joker = LiveJokerFactory().create(
        {
            "center": "j_juggler",
            "label": "Juggler",
            "cost": 4.5,
        }
    )

    assert joker is not None
    assert joker.cost == 4.5
    assert type(joker.cost) is float
