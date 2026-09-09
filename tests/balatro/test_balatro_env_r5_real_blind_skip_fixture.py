import hashlib
import json
import lzma
from pathlib import Path

from games.balatro.live.blind_skip_parity_capture import (
    blind_skip_parity_checkpoint_from_payload,
)
from games.balatro.live.blind_skip_parity_checkpoint import (
    compare_live_blind_skip_replay,
)
from games.balatro.live.parity_capture import (
    successful_skip_blind_evidence_from_run_rows,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "r5"
PUBLIC_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260909T150330Z-186b22a6-attempt-005.skip-economy.jsonl.xz"
)
PRIVATE_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260909T150330Z-186b22a6-attempt-005.blind-skip-parity.jsonl.xz"
)
_PUBLIC_SHA256 = "20898032d15279b00397eef9bbc530989931fd0a90df2fdc998e4d98d336cf29"
_PRIVATE_SHA256 = "e79c97beb6634d5c230ca02a49e62085bac0486c2be46988af6ecbd5bc465d2c"


def _fixture_bytes(path: Path) -> bytes:
    with lzma.open(path, "rb") as handle:
        return handle.read()


def _fixture_rows(path: Path):
    return [
        json.loads(line)
        for line in _fixture_bytes(path).decode("utf-8").splitlines()
    ]


def test_env_r5_real_economy_skip_fixture_preserves_exact_live_boundary():
    public_raw = _fixture_bytes(PUBLIC_FIXTURE)
    private_raw = _fixture_bytes(PRIVATE_FIXTURE)
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_rows = _fixture_rows(PRIVATE_FIXTURE)

    assert hashlib.sha256(public_raw).hexdigest() == _PUBLIC_SHA256
    assert hashlib.sha256(private_raw).hexdigest() == _PRIVATE_SHA256
    assert [row["sequence"] for row in public_rows] == [243, 244, 245]
    assert [row["event"] for row in public_rows] == [
        "observation",
        "decision",
        "action_result",
    ]
    assert public_rows[1]["data"]["action"] == {"name": "SKIP_BLIND"}
    assert public_rows[2]["data"]["success"] is True
    assert len(private_rows) == 1
    assert private_rows[0]["schema"] == "balatro-r5-blind-skip-parity-v1"
    # Preserve the original pre-repair verdict. The fixture is evidence, not a
    # rewritten success record; the current canonical replay must prove the fix.
    assert private_rows[0]["comparison"] == {
        "differences": ["public.after"],
        "matches": False,
        "public_differences": ["after"],
        "public_matches": False,
    }


def test_env_r5_real_economy_skip_replays_through_exact_owner():
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_row = _fixture_rows(PRIVATE_FIXTURE)[0]
    live = successful_skip_blind_evidence_from_run_rows(public_rows)
    before = blind_skip_parity_checkpoint_from_payload(private_row["before"])
    after = blind_skip_parity_checkpoint_from_payload(private_row["after"])

    assert len(live) == 1
    assert before.public_snapshot.payload["money"] == 36
    assert after.public_snapshot.payload["money"] == 72
    assert before.skips == 0
    assert after.skips == 1
    assert before.progression.small_status == "Select"
    assert after.progression.small_status == "Skipped"
    assert after.progression.big_status == "Select"
    assert after.progression.blind_on_deck == "Big"
    assert before.progression.small_tag == "tag_economy"
    assert after.progression.big_tag == "tag_juggle"
    assert before.active_tag_count == after.active_tag_count == 0

    comparison = compare_live_blind_skip_replay(before, after, live[0])

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.public.matches is True
    assert comparison.public.differences == ()
