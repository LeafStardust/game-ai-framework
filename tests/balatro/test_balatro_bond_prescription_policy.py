from types import SimpleNamespace

import games.balatro.bond_prescription_policy as policy


def card(rank="", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement, seal=seal)


def test_baron_prescription_prefers_steel_creation_and_king_target(monkeypatch):
    monkeypatch.setattr(policy, "_active_motif_ids", lambda state: frozenset({"baron_mime_steel"}))
    bonus, notes = policy.prescription_bonus(
        object(),
        kind="TAROT",
        label="The Chariot",
        cards=(card(rank="K"),),
    )
    assert bonus == 1.75
    assert any("Steel creation" in note for note in notes)
    assert any("King engine" in note for note in notes)


def test_baron_prescription_values_red_seal_steel_king_playing_card(monkeypatch):
    monkeypatch.setattr(policy, "_active_motif_ids", lambda state: frozenset({"baron_mime_steel"}))
    bonus, _ = policy.prescription_bonus(
        object(),
        kind="PLAYING_CARD",
        label="King of Spades",
        playing_card=card(rank="K", enhancement="Steel", seal="Red"),
    )
    assert bonus == 2.30


def test_burnt_planet_uses_actual_target_hand_not_default(monkeypatch):
    monkeypatch.setattr(policy, "_active_motif_ids", lambda state: frozenset({"burnt_target_level"}))
    monkeypatch.setattr(policy, "_burnt_target_hand", lambda state: "PAIR")
    mercury, mercury_notes = policy.prescription_bonus(object(), kind="PLANET", label="Mercury")
    pluto, _ = policy.prescription_bonus(object(), kind="PLANET", label="Pluto")
    assert mercury == 1.50
    assert pluto == 0.0
    assert any("PAIR" in note for note in mercury_notes)


def test_photo_chad_and_hack_target_red_seals_differently(monkeypatch):
    monkeypatch.setattr(
        policy,
        "_active_motif_ids",
        lambda state: frozenset({"photograph_hanging_chad", "low_rank_hack_retrigger"}),
    )
    face_bonus, _ = policy.prescription_bonus(
        object(), kind="SPECTRAL", label="Deja Vu", cards=(card(rank="Q"),)
    )
    low_bonus, _ = policy.prescription_bonus(
        object(), kind="SPECTRAL", label="Deja Vu", cards=(card(rank="3"),)
    )
    assert face_bonus == 2.00
    assert low_bonus == 2.00


def test_prescription_bonus_is_bounded(monkeypatch):
    monkeypatch.setattr(
        policy,
        "_active_motif_ids",
        lambda state: frozenset({
            "baron_mime_steel",
            "photograph_hanging_chad",
            "low_rank_hack_retrigger",
        }),
    )
    bonus, _ = policy.prescription_bonus(
        object(), kind="SPECTRAL", label="Deja Vu", cards=(card(rank="K"),)
    )
    assert bonus <= 2.50


def test_no_active_motif_means_no_prescription(monkeypatch):
    monkeypatch.setattr(policy, "_active_motif_ids", lambda state: frozenset())
    bonus, notes = policy.prescription_bonus(
        object(), kind="TAROT", label="The Chariot", cards=(card(rank="K"),)
    )
    assert bonus == 0.0
    assert notes == ()
