from games.balatro.live.external import ColorGridSignature, PhaseTemplate
from games.balatro.live.external.phase_dataset import merge_phase_template_sources
from games.balatro.live.external.phase_templates import (
    load_phase_templates,
    save_phase_templates,
)


def _template(phase: str, value: int) -> PhaseTemplate:
    return PhaseTemplate(
        phase=phase,
        signature=ColorGridSignature(
            columns=2,
            rows=2,
            values=tuple([value] * 12),
        ),
    )


def test_phase_dataset_merge_replaces_only_source_phases(tmp_path):
    base = tmp_path / "base.json"
    blind_small = tmp_path / "blind-small.json"
    blind_big = tmp_path / "blind-big.json"
    hand_a = tmp_path / "hand-a.json"

    save_phase_templates(
        base,
        [
            _template("BLIND_SELECT", 10),
            _template("ROUND_EVAL", 20),
            _template("SELECTING_HAND", 30),
            _template("SHOP", 40),
        ],
    )
    save_phase_templates(
        blind_small,
        [_template("BLIND_SELECT", 50), _template("BLIND_SELECT", 51)],
    )
    save_phase_templates(
        blind_big,
        [_template("BLIND_SELECT", 60), _template("BLIND_SELECT", 61)],
    )
    save_phase_templates(
        hand_a,
        [_template("SELECTING_HAND", 70), _template("SELECTING_HAND", 71)],
    )

    counts = merge_phase_template_sources(
        base,
        [blind_small, blind_big, hand_a],
    )
    merged = load_phase_templates(base)

    assert counts == {
        "BLIND_SELECT": 4,
        "ROUND_EVAL": 1,
        "SELECTING_HAND": 2,
        "SHOP": 1,
    }
    assert [
        template.signature.values[0]
        for template in merged
        if template.phase == "ROUND_EVAL"
    ] == [20]
    assert [
        template.signature.values[0]
        for template in merged
        if template.phase == "SHOP"
    ] == [40]


def test_phase_dataset_merge_can_write_separate_output(tmp_path):
    base = tmp_path / "base.json"
    source = tmp_path / "blind.json"
    output = tmp_path / "merged.json"

    save_phase_templates(base, [_template("SHOP", 10)])
    save_phase_templates(source, [_template("BLIND_SELECT", 20)])

    merge_phase_template_sources(
        base,
        [source],
        output_path=output,
    )

    assert [template.phase for template in load_phase_templates(base)] == ["SHOP"]
    assert {template.phase for template in load_phase_templates(output)} == {
        "BLIND_SELECT",
        "SHOP",
    }


def test_phase_dataset_merge_rejects_mixed_phase_source(tmp_path):
    base = tmp_path / "base.json"
    source = tmp_path / "mixed.json"

    save_phase_templates(base, [_template("SHOP", 10)])
    save_phase_templates(
        source,
        [_template("BLIND_SELECT", 20), _template("SELECTING_HAND", 30)],
    )

    try:
        merge_phase_template_sources(base, [source])
    except ValueError as error:
        assert "exactly one phase" in str(error)
    else:
        raise AssertionError("mixed-phase dataset source should be rejected")


def test_phase_dataset_merge_requires_source_for_explicit_replacement(tmp_path):
    base = tmp_path / "base.json"
    source = tmp_path / "blind.json"

    save_phase_templates(base, [_template("SHOP", 10)])
    save_phase_templates(source, [_template("BLIND_SELECT", 20)])

    try:
        merge_phase_template_sources(
            base,
            [source],
            replace_phases={"BLIND_SELECT", "SELECTING_HAND"},
        )
    except ValueError as error:
        assert "SELECTING_HAND" in str(error)
    else:
        raise AssertionError("missing replacement source should be rejected")
