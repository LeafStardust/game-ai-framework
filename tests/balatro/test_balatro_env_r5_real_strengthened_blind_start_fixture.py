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
    / "balatro-20260911T153744Z-7b05a35c-attempt-001.select-small.jsonl.xz"
)
PRIVATE_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260911T153744Z-7b05a35c-attempt-001.blind-start-parity.jsonl.xz"
)
_PUBLIC_SHA256 = "0e75490fd5018bcd1fbcf8e3364ed65c492c084716fe712521c33e4035de3fd5"
_PRIVATE_SHA256 = "1250495c0e636eb79cdb3b58cf642db103cf01434dff0c414598298ba201ac23"


def _fixture_bytes(path: Path) -> bytes:
    with lzma.open(path, "rb") as handle:
        return handle.read()


def _fixture_rows(path: Path):
    return [json.loads(line) for line in _fixture_bytes(path).decode("utf-8").splitlines()]


def test_env_r5_strengthened_small_blind_fixture_preserves_exact_live_boundary():
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
    assert private_rows[0]["comparison"] == {
        "differences": [],
        "matches": True,
        "public_differences": [],
        "public_matches": True,
    }


def test_env_r5_strengthened_small_blind_fixture_replays_private_draw_order():
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_row = _fixture_rows(PRIVATE_FIXTURE)[0]
    live = successful_select_blind_evidence_from_run_rows(public_rows)
    before = blind_start_parity_checkpoint_from_payload(private_row["before"])
    after = blind_start_parity_checkpoint_from_payload(private_row["after"])

    assert len(live) == 1
    assert before.draw_pile_live_ids is None
    assert len(after.draw_pile_live_ids or ()) == 44

    comparison = compare_live_blind_start_replay(before, after, live[0])

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.public.matches is True
    assert comparison.public.differences == ()
