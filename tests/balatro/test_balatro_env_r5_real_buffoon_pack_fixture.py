from copy import deepcopy
import hashlib
import json
import lzma
from pathlib import Path
from types import SimpleNamespace

from games.balatro.actions import BalatroAction, SELECT_PACK_CARD
from games.balatro.env.strategic_evidence import (
    choose_pack_option_with_public_evidence,
)
from games.balatro.live.buffoon_pack_parity_capture import (
    _snapshot_from_payload,
    buffoon_pack_parity_checkpoint_from_payload,
    compare_captured_live_buffoon_pack,
    headless_buffoon_pack_run_from_checkpoint,
)
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_buffoon_pack_evidence,
    successful_buffoon_pack_evidence_from_run_rows,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "r5"
PUBLIC_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260909T190805Z-9926231c-attempt-001.choose-shoot-the-moon.jsonl.xz"
)
PRIVATE_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260909T190805Z-9926231c-attempt-001.buffoon-pack-parity.jsonl.xz"
)
_PUBLIC_SHA256 = "7a64b8d9c32edd0cfa4d797d386306e5e79634e03e7b76847920b241729cbbc4"
_PRIVATE_SHA256 = "ae2647debda96a644b4416e28c85375fcf21cbe66713e4c30ed86fbe857048f8"


def _fixture_bytes(path: Path) -> bytes:
    with lzma.open(path, "rb") as handle:
        return handle.read()


def _fixture_rows(path: Path):
    return [
        json.loads(line)
        for line in _fixture_bytes(path).decode("utf-8").splitlines()
    ]


def _captured_action(private_row, checkpoint):
    option_index = private_row["action"]["option_index"]
    choice = checkpoint.choices[option_index]
    return BalatroAction(
        SELECT_PACK_CARD,
        target=SimpleNamespace(
            area_index=option_index,
            label=choice["label"],
            live_id=choice["live_id"],
            data=deepcopy(choice),
        ),
    )


def test_env_r5_real_buffoon_fixture_preserves_exact_live_boundary():
    public_raw = _fixture_bytes(PUBLIC_FIXTURE)
    private_raw = _fixture_bytes(PRIVATE_FIXTURE)
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_rows = _fixture_rows(PRIVATE_FIXTURE)

    assert hashlib.sha256(public_raw).hexdigest() == _PUBLIC_SHA256
    assert hashlib.sha256(private_raw).hexdigest() == _PRIVATE_SHA256
    assert [row["sequence"] for row in public_rows] == [25, 26, 27]
    assert [row["event"] for row in public_rows] == [
        "observation",
        "decision",
        "action_result",
    ]
    assert public_rows[1]["data"]["action"] == {
        "name": "SELECT_PACK_CARD",
        "target": {"area_index": 0, "label": "Shoot the Moon"},
    }
    assert public_rows[2]["data"]["success"] is True
    assert len(private_rows) == 1
    assert private_rows[0]["schema"] == "balatro-r5-buffoon-pack-parity-v1"
    # Preserve the recorder's original pre-repair verdict unchanged.
    assert private_rows[0]["comparison"] == {
        "differences": ["public.after"],
        "matches": False,
    }


def test_env_r5_real_buffoon_fixture_replays_through_exact_pack_owner():
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    private_row = _fixture_rows(PRIVATE_FIXTURE)[0]
    checkpoint = buffoon_pack_parity_checkpoint_from_payload(private_row["before"])
    option_index = private_row["action"]["option_index"]
    run = headless_buffoon_pack_run_from_checkpoint(checkpoint)

    result, simulator = choose_pack_option_with_public_evidence(
        run,
        option_index=option_index,
    )
    public_comparison = compare_run_rows_to_simulator_buffoon_pack_evidence(
        public_rows,
        (simulator,),
    )
    private_comparison = compare_captured_live_buffoon_pack(
        checkpoint,
        _captured_action(private_row, checkpoint),
        _snapshot_from_payload(private_row["after_public_snapshot"]),
    )

    live = successful_buffoon_pack_evidence_from_run_rows(public_rows)
    assert len(live) == 1
    assert live[0].action.payload() == {"option_index": 0}
    assert [joker.center for joker in result.public.jokers] == ["j_shoot_the_moon"]
    assert "j_droll" in {
        record["key"] for record in result.public.joker_generation_pools["1"]
    }
    assert "j_shoot_the_moon" not in {
        record["key"] for record in result.public.joker_generation_pools["1"]
    }
    assert public_comparison.matches is True
    assert public_comparison.differences == ()
    assert private_comparison.matches is True
    assert private_comparison.differences == ()
