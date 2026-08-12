from games.balatro.live.external.live_memory_pack_action_injected_validation import (
    _choice_signature,
    _guard_errors,
)
from games.balatro.live.pack import LivePackChoice


def _choice(index=0, *, label="Mercury", center="c_mercury", live_id=101, kind="Planet"):
    return LivePackChoice(
        area_index=index,
        address=0x1000 + index,
        data={
            "area_index": index,
            "live_id": live_id,
            "label": label,
            "center": center,
            "ability_set": kind,
        },
    )


def test_pack_select_guard_accepts_exact_visible_choice():
    errors = _guard_errors(
        phase="PLANET_PACK",
        state_complete=True,
        choices=[_choice()],
        action_name="SELECT_PACK_CARD",
        expected_phase="PLANET_PACK",
        index=0,
        expected_label="Mercury",
        expected_center="c_mercury",
    )

    assert errors == []


def test_pack_select_guard_blocks_changed_choice_identity():
    errors = _guard_errors(
        phase="PLANET_PACK",
        state_complete=True,
        choices=[_choice(label="Venus", center="c_venus")],
        action_name="SELECT_PACK_CARD",
        expected_phase="PLANET_PACK",
        index=0,
        expected_label="Mercury",
        expected_center="c_mercury",
    )

    assert "expected label 'Mercury', observed 'Venus'" in errors
    assert "expected center 'c_mercury', observed 'c_venus'" in errors


def test_pack_select_guard_blocks_wrong_phase_and_missing_index():
    errors = _guard_errors(
        phase="SHOP",
        state_complete=True,
        choices=[],
        action_name="SELECT_PACK_CARD",
        expected_phase="PLANET_PACK",
        index=0,
        expected_label="Mercury",
        expected_center="c_mercury",
    )

    assert "expected a *_PACK phase, observed SHOP" in errors
    assert "expected phase PLANET_PACK, observed SHOP" in errors
    assert "pack choice index 0 is not currently visible" in errors


def test_pack_skip_guard_needs_only_exact_settled_pack_phase():
    errors = _guard_errors(
        phase="PLANET_PACK",
        state_complete=True,
        choices=[_choice()],
        action_name="SKIP_BOOSTER",
        expected_phase="PLANET_PACK",
    )

    assert errors == []


def test_choice_signature_changes_when_visible_pack_choice_changes():
    before = [_choice()]
    after = [_choice(label="Venus", center="c_venus", live_id=102)]

    assert _choice_signature(before) != _choice_signature(after)
