from pathlib import Path


def test_shop_arbiter_reuses_standalone_joker_decisions_and_avoids_nested_projected_d2():
    source = Path("games/balatro/shop_arbiter.py").read_text(encoding="utf-8")

    assert "standalone_joker_decisions = tuple(" in source
    assert source.count("standalone=standalone_joker_decisions") >= 2

    pair_body = source.split("def _best_visible_bond_pair(", 1)[1].split(
        "def _standalone_add_option", 1
    )[0]
    assert "policy.decide(projected" not in pair_body
    assert "_bond_transition_bonus(projected, second)" in pair_body
    assert "projected_advantage <= policy.thresholds.minimum_purchase_advantage" in pair_body
