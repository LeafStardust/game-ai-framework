from types import SimpleNamespace

from games.balatro.bonds.behavior_strategy import _motif_source_match as behavior_motif_source_match
from games.balatro.bonds.motifs import MotifEvaluation, MotifState
from games.balatro.bonds.strategy_semantics import _motif_source_match as role_motif_source_match


def _motif():
    return MotifEvaluation(
        motif_id="baron_mime_steel",
        state=MotifState.POTENTIAL,
        relevant_bonds=("held_cards", "held_retrigger", "steel", "kings"),
        present_components=("BARON", "MIME"),
        missing_components=("STEEL", "KINGS"),
        prescriptions=(),
    )


def test_role_strategy_motif_acceleration_requires_actual_present_components():
    motif = _motif()

    assert role_motif_source_match(motif, ("BaronJoker", "MimeJoker")) is True
    assert role_motif_source_match(motif, ("BaronJoker", "Steel Card Density")) is False
    assert role_motif_source_match(motif, ("UnrelatedJoker", "MimeJoker")) is False


def test_behavior_strategy_motif_acceleration_ignores_ambient_feature_substitutes():
    motif = _motif()
    actual_pair = (
        SimpleNamespace(source="BaronJoker"),
        SimpleNamespace(source="MimeJoker"),
    )
    ambient_substitute = (
        SimpleNamespace(source="BaronJoker"),
        SimpleNamespace(source="feature:enhancement:steel"),
    )

    assert behavior_motif_source_match(motif, actual_pair) is True
    assert behavior_motif_source_match(motif, ambient_substitute) is False
