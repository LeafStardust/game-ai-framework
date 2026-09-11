import hashlib
import json
import lzma
from pathlib import Path
from types import SimpleNamespace

from games.balatro.actions import USE_CONSUMABLE, BalatroAction
from games.balatro.env.strategic_evidence import use_planet_with_public_evidence
from games.balatro.live.held_planet_parity_capture import (
    _snapshot_from_payload,
    _usage_from_payload,
    compare_captured_live_held_planet,
    held_planet_parity_checkpoint_from_payload,
    headless_held_planet_run_from_checkpoint,
)
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_held_planet_use_evidence,
    successful_held_planet_use_evidence_from_run_rows,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "r5"
PUBLIC_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260911T153744Z-7b05a35c-attempt-004.use-uranus.jsonl.xz"
)
PRIVATE_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260911T153744Z-7b05a35c-attempt-004.held-planet-parity.jsonl.xz"
)
_PUBLIC_SHA256 = "b5fe16efed40bedff785c7c4222360a58ed98172f3002fefee7756d6e71f1846"
_PRIVATE_SHA256 = "15084675890d6afcb9acf403d9aa98c930476fbd4b2388cd8982cf736e6a338f"


def _fixture_bytes(path: Path) -> bytes:
    with lzma.open(path, "rb") as handle:
        return handle.read()


def _fixture_rows(path: Path):
    return [json.loads(line) for line in _fixture_bytes(path).decode("utf-8").splitlines()]


def test_env_r5_real_held_uranus_fixture_preserves_exact_live_boundary():
    public_raw = _fixture_bytes(PUBLIC_FIXTURE)
    private_raw = _fixture_bytes(PRIVATE_FIXTURE)
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_rows = _fixture_rows(PRIVATE_FIXTURE)

    assert hashlib.sha256(public_raw).hexdigest() == _PUBLIC_SHA256
    assert hashlib.sha256(private_raw).hexdigest() == _PRIVATE_SHA256
    assert [row["sequence"] for row in public_rows] == [187, 189, 190]
    assert [row["event"] for row in public_rows] == [
        "observation",
        "decision",
        "action_result",
    ]
    assert public_rows[1]["data"]["action"] == {
        "name": "USE_CONSUMABLE",
        "target": {"area_index": 0, "name": "Uranus", "price": 3},
    }
    assert public_rows[2]["data"]["success"] is True
    assert len(private_rows) == 1
    assert private_rows[0]["schema"] == "balatro-r5-held-planet-parity-v1"
    assert private_rows[0]["comparison"] == {
        "differences": ["public.after"],
        "matches": False,
    }


def test_env_r5_real_held_uranus_fixture_replays_unchanged_through_exact_owner():
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_row = _fixture_rows(PRIVATE_FIXTURE)[0]
    live = successful_held_planet_use_evidence_from_run_rows(public_rows)
    before = held_planet_parity_checkpoint_from_payload(private_row["before"])
    after_snapshot = _snapshot_from_payload(private_row["after_public_snapshot"])
    after_usage = _usage_from_payload(private_row["after_usage"])
    run = headless_held_planet_run_from_checkpoint(before)

    assert len(live) == 1
    assert live[0].before.consumables[0].name == "Uranus"
    assert before.usage.counts == {}
    assert after_usage.counts == {"c_uranus": 1}

    result, simulator = use_planet_with_public_evidence(run, consumable_index=0)
    public_comparison = compare_run_rows_to_simulator_held_planet_use_evidence(
        public_rows,
        (simulator,),
    )
    action = BalatroAction(
        USE_CONSUMABLE,
        target=SimpleNamespace(area_index=0, name="Uranus", label="Uranus"),
    )
    private_comparison = compare_captured_live_held_planet(
        before,
        action,
        after_snapshot,
        after_usage,
    )

    assert result.public.consumables == []
    assert result.public.last_tarot_planet == "c_uranus"
    assert result.consumable_usage_counts == {"c_uranus": 1}
    assert public_comparison.matches is True
    assert public_comparison.differences == ()
    assert private_comparison.matches is True
    assert private_comparison.differences == ()
