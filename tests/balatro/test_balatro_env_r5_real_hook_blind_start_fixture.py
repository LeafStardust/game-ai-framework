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
    / "balatro-20260911T180643Z-11e1fb92-attempt-001.select-hook.jsonl.xz"
)
PRIVATE_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260911T180643Z-11e1fb92-attempt-001.hook-blind-start-parity.jsonl.xz"
)
_PUBLIC_SHA256 = "95078f426df4796adcda8142ebb080b2738a319f62feefa3636fadbf21e0f510"
_PRIVATE_SHA256 = "1d45b7c74f6f0ebb4235ff136d2ca83252dfd736cc51c5ff16f7091c18711ec3"


def _fixture_bytes(path: Path) -> bytes:
    with lzma.open(path, "rb") as handle:
        return handle.read()


def _fixture_rows(path: Path):
    return [json.loads(line) for line in _fixture_bytes(path).decode("utf-8").splitlines()]


def test_env_r5_real_hook_start_fixture_preserves_exact_live_boundary():
    public_raw = _fixture_bytes(PUBLIC_FIXTURE)
    private_raw = _fixture_bytes(PRIVATE_FIXTURE)
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_rows = _fixture_rows(PRIVATE_FIXTURE)

    assert hashlib.sha256(public_raw).hexdigest() == _PUBLIC_SHA256
    assert hashlib.sha256(private_raw).hexdigest() == _PRIVATE_SHA256
    assert [row["sequence"] for row in public_rows] == [49, 50, 51]
    assert [row["event"] for row in public_rows] == [
        "observation",
        "decision",
        "action_result",
    ]
    assert public_rows[0]["data"]["state"]["payload"]["blind"] == {
        "key": "bl_hook",
        "name": "The Hook",
        "reward": 5,
        "score": 600,
        "status": "SELECT",
        "type": "BOSS",
    }
    assert public_rows[1]["data"]["action"] == {"name": "SELECT_BLIND"}
    assert public_rows[2]["data"]["success"] is True
    assert len(private_rows) == 1
    assert private_rows[0]["schema"] == "balatro-r5-blind-start-parity-v1"
    assert private_rows[0]["sequence"] == 3
    assert private_rows[0]["comparison"] == {
        "differences": ["public.after"],
        "matches": False,
        "public_differences": ["after"],
        "public_matches": False,
    }


def test_env_r5_real_hook_start_fixture_replays_exact_facing_and_draw_order():
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_row = _fixture_rows(PRIVATE_FIXTURE)[0]
    live = successful_select_blind_evidence_from_run_rows(public_rows)
    before = blind_start_parity_checkpoint_from_payload(private_row["before"])
    after = blind_start_parity_checkpoint_from_payload(private_row["after"])

    assert len(live) == 1
    assert live[0].before.boss_name == "The Hook"
    assert all(not card.face_down for card in live[0].after.hand)
    assert all(card.facing_observed for card in live[0].after.hand)
    assert before.draw_pile_live_ids is None
    assert len(after.draw_pile_live_ids or ()) == 44

    comparison = compare_live_blind_start_replay(before, after, live[0])

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.public.matches is True
    assert comparison.public.differences == ()
