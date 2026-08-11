from games.balatro.card import BalatroCard
from games.balatro.live.depth_draw_outcomes import DepthAwarePublicDrawOutcomeModel
from games.balatro.live.draw_model import PublicDeckComposition


def _composition(count: int):
    suits = ("Spades", "Hearts", "Clubs", "Diamonds")
    cards = [
        BalatroCard(str((index % 9) + 2), suits[index % len(suits)])
        for index in range(count)
    ]
    return PublicDeckComposition.from_cards(cards)


def test_depth_aware_draw_sampling_uses_root_then_child_sample_counts():
    model = DepthAwarePublicDrawOutcomeModel(
        exact_combination_limit=1,
        root_sample_count=4,
        child_sample_count=2,
        seed=7,
    )

    root = model.distribution(_composition(20), 2)
    child = model.distribution(_composition(18), 2)

    assert root.exact is False
    assert root.sample_count == 4
    assert child.exact is False
    assert child.sample_count == 2


def test_depth_aware_draw_sampling_keeps_small_spaces_exact():
    model = DepthAwarePublicDrawOutcomeModel(
        exact_combination_limit=100,
        root_sample_count=4,
        child_sample_count=2,
        seed=7,
    )

    root = model.distribution(_composition(4), 1)
    child = model.distribution(_composition(3), 1)

    assert root.exact is True
    assert child.exact is True
