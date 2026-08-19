from games.balatro.card import BalatroCard
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
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


def test_depth_aware_draw_sampling_does_not_exactly_expand_large_one_card_children():
    model = DepthAwarePublicDrawOutcomeModel(
        exact_combination_limit=128,
        root_sample_count=4,
        child_sample_count=1,
        seed=7,
    )

    root = model.distribution(_composition(44), 1)
    child = model.distribution(_composition(41), 1)

    # Root keeps the generous exact limit: 44 one-card outcomes are tractable.
    assert root.exact is True
    assert root.combination_count == 44

    # Child uses the tighter default exact limit (8), so the same kind of
    # one-card redraw is sampled instead of recursively expanding 41 branches.
    assert child.exact is False
    assert child.combination_count == 41
    assert child.sample_count == 1
    assert len(child.outcomes) == 1


def test_depth_aware_draw_sampling_can_reset_a_new_authoritative_root():
    model = DepthAwarePublicDrawOutcomeModel(
        exact_combination_limit=128,
        root_sample_count=4,
        child_sample_count=1,
        seed=7,
    )

    first_root = model.distribution(_composition(44), 1)
    first_child = model.distribution(_composition(41), 1)
    assert first_root.exact is True
    assert first_child.exact is False

    model.reset_root()
    replanned_root = model.distribution(_composition(41), 1)

    # After a real checkpoint, the new authoritative 41-card population must be
    # treated as a fresh root, not as a child of the old 44-card search.
    assert replanned_root.exact is True
    assert replanned_root.combination_count == 41


def test_live_planner_resets_depth_aware_draw_root_before_each_search():
    model = DepthAwarePublicDrawOutcomeModel(
        exact_combination_limit=128,
        root_sample_count=4,
        child_sample_count=1,
        seed=7,
    )
    model.distribution(_composition(44), 1)
    assert model._root_population_size == 44

    planner = LiveBlindClearPlanner(draw_outcomes=model)
    planner.reset_search_stats()

    assert model._root_population_size is None
