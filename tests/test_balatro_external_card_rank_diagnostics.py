from games.balatro.live.external.card_rank_diagnostics import exact_rank_collisions
from games.balatro.live.external.card_templates import (
    CardTemplateSet,
    CardVisualTemplate,
    save_card_template_set,
)


def _signature(value: int) -> tuple[int, ...]:
    return (value,) * 400


def test_exact_rank_collisions_reports_cross_rank_duplicates(tmp_path):
    path = tmp_path / "templates.json"
    save_card_template_set(
        path,
        CardTemplateSet(
            20,
            20,
            (
                CardVisualTemplate("A", _signature(0)),
                CardVisualTemplate("K", _signature(0)),
                CardVisualTemplate("Q", _signature(255)),
            ),
            (CardVisualTemplate("Spades", (20, 30, 40)),),
        ),
    )

    collisions = exact_rank_collisions(path)

    assert len(collisions) == 1
    assert collisions[0][0] == ("A", "K")


def test_exact_rank_collisions_ignores_duplicate_samples_of_same_rank(tmp_path):
    path = tmp_path / "templates.json"
    save_card_template_set(
        path,
        CardTemplateSet(
            20,
            20,
            (
                CardVisualTemplate("K", _signature(0)),
                CardVisualTemplate("K", _signature(0)),
                CardVisualTemplate("Q", _signature(255)),
            ),
            (CardVisualTemplate("Spades", (20, 30, 40)),),
        ),
    )

    assert exact_rank_collisions(path) == []
