from games.balatro.reroll_joker_expectation_policy import _bounded_editions


def test_small_public_pool_keeps_all_edition_branches_exact():
    editions = (
        (None, 0.92),
        ("FOIL", 0.04),
        ("HOLOGRAPHIC", 0.03),
        ("POLYCHROME", 0.01),
    )

    assert _bounded_editions(editions, exact=True) == editions


def test_large_public_pool_keeps_only_most_probable_edition_without_renormalizing():
    editions = (
        (None, 0.92),
        ("FOIL", 0.04),
        ("HOLOGRAPHIC", 0.03),
        ("POLYCHROME", 0.01),
    )

    bounded = _bounded_editions(editions, exact=False)

    assert bounded == ((None, 0.92),)
    assert sum(probability for _, probability in bounded) == 0.92


def test_large_public_pool_edition_tie_break_is_stable():
    editions = (
        ("FIRST", 0.5),
        ("SECOND", 0.5),
    )

    assert _bounded_editions(editions, exact=False) == (("FIRST", 0.5),)
