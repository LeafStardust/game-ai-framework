from types import SimpleNamespace

import games.balatro.strategy_resource_coherence_policy as policy
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy


def test_seek_bond_face_cards_becomes_card_level_pack_demand(monkeypatch):
    candidate = SimpleNamespace(
        strategy_id="face_cards",
        prescriptions=("seek_bond:face_cards:R2",),
    )
    monkeypatch.setattr(policy, "_strategy_candidate", lambda state: candidate)

    features = policy._strategy_features(object())

    assert features == ("rank:J", "rank:Q", "rank:K")


def test_existing_target_cards_still_create_density_demand(monkeypatch):
    candidate = SimpleNamespace(
        strategy_id="face_cards",
        prescriptions=("seek_bond:face_cards:R2",),
    )
    monkeypatch.setattr(policy, "_strategy_candidate", lambda state: candidate)
    profile = SimpleNamespace(
        enhancement_counts=(),
        seal_counts=(),
        edition_counts=(),
        deck_size=52,
        strength=lambda feature: 1.0,
        can_produce=lambda feature: False,
    )

    need, rationale = policy._strategy_card_need(
        BuildAwareShopBoosterPolicy(),
        object(),
        profile,
        "STANDARD",
    )

    assert need == 0.45
    assert any("strategy relevant card goals=" in line for line in rationale)
