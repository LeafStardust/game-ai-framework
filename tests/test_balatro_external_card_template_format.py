import json

import pytest

from games.balatro.live.external.card_template_format import (
    RANK_FEATURE,
    SUIT_FEATURE,
    TEMPLATE_VERSION,
    load_card_template_set,
    save_card_template_set,
)
from games.balatro.live.external.card_templates import CardTemplateSet, CardVisualTemplate


def _templates():
    return CardTemplateSet(
        columns=2,
        rows=2,
        ranks=(CardVisualTemplate("A", (0, 64, 128, 255)),),
        suits=(CardVisualTemplate("Spades", (36, 44, 86)),),
    )


def test_v5_template_format_round_trips_feature_metadata(tmp_path):
    path = tmp_path / "templates.json"

    save_card_template_set(path, _templates())
    payload = json.loads(path.read_text(encoding="utf-8"))
    loaded = load_card_template_set(path)

    assert payload["version"] == TEMPLATE_VERSION == 5
    assert payload["rank_feature"] == RANK_FEATURE
    assert payload["suit_feature"] == SUIT_FEATURE
    assert loaded == _templates()


def test_v5_template_format_rejects_feature_mismatch(tmp_path):
    path = tmp_path / "templates.json"
    save_card_template_set(path, _templates())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["rank_feature"] = "obsolete"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="rank feature"):
        load_card_template_set(path)
