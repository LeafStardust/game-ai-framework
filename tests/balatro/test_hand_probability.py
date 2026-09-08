from games.balatro.probability import HandProbability


def test_draw_probability_returns_value():

    probability = HandProbability()

    result = probability.draw_probability(
        10,
        50,
        1
    )

    assert result > 0
    assert result <= 1