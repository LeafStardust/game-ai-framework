import hashlib
import json
import lzma
from pathlib import Path

from games.balatro.live.blind_start_parity_capture import (
    blind_start_parity_checkpoint_from_payload,
)
from games.balatro.live.blind_start_parity_checkpoint import (
    compare_live_blind_start_replay,
)
from games.balatro.live.parity_capture import (
    successful_select_blind_evidence_from_run_rows,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "r5"
PUBLIC_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260909T090428Z-a5968591-attempt-001.select-small.jsonl.xz"
)
PRIVATE_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260909T090428Z-a5968591-attempt-001.blind-start-parity.jsonl.xz"
)
_PUBLIC_SHA256 = "1c3823b66bbbc3559332f8f38369507483edec8d49c00007929064c307ad7d64"
_PRIVATE_SHA256 = "f353095e5cd93caee6a82e3ea85b848e7a5f7a14df95fe49d9ea8f21cb81feb5"


def _fixture_bytes(path: Path) -> bytes:
    with lzma.open(path, "rb") as handle:
        return handle.read()


def _fixture_rows(path: Path):
    return [
        json.loads(line)
        for line in _fixture_bytes(path).decode("utf-8").splitlines()
    ]


def test_env_r5_real_small_blind_fixture_preserves_exact_live_boundary():
    public_raw = _fixture_bytes(PUBLIC_FIXTURE)
    private_raw = _fixture_bytes(PRIVATE_FIXTURE)
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_rows = _fixture_rows(PRIVATE_FIXTURE)

    assert hashlib.sha256(public_raw).hexdigest() == _PUBLIC_SHA256
    assert hashlib.sha256(private_raw).hexdigest() == _PRIVATE_SHA256
    assert [row["sequence"] for row in public_rows] == [2, 4, 5]
    assert [row["event"] for row in public_rows] == [
        "observation",
        "decision",
        "action_result",
    ]
    assert public_rows[1]["data"]["action"] == {"name": "SELECT_BLIND"}
    assert public_rows[2]["data"]["success"] is True
    assert len(private_rows) == 1
    assert private_rows[0]["schema"] == "balatro-r5-blind-start-parity-v1"
    assert private_rows[0]["sequence"] == 1
    assert private_rows[0]["comparison"] == {
        "differences": [],
        "matches": True,
        "public_differences": [],
        "public_matches": True,
    }


def test_env_r5_real_small_blind_fixture_replays_unchanged_through_exact_owner():
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_row = _fixture_rows(PRIVATE_FIXTURE)[0]
    live = successful_select_blind_evidence_from_run_rows(public_rows)
    before = blind_start_parity_checkpoint_from_payload(private_row["before"])
    after = blind_start_parity_checkpoint_from_payload(private_row["after"])

    assert len(live) == 1
    assert before.active_tag_count == 0
    assert after.active_tag_count == 0
    assert before.public_snapshot.payload["blind"]["score"] == 300
    assert after.public_snapshot.payload["blind"]["score"] == 300

    comparison = compare_live_blind_start_replay(before, after, live[0])

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.public.matches is True
    assert comparison.public.differences == ()
