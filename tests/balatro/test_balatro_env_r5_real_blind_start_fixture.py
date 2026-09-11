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
    _snapshot_from_log_state,
    successful_select_blind_evidence_from_run_rows,
)
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.env.parity import canonical_public_state_signature
from games.balatro.env.round_end import cash_out_baseline_ordinary_blind
from games.balatro.env.transition import HeadlessRunState


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "r5"
PUBLIC_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260909T090428Z-a5968591-attempt-001.select-small.jsonl.xz"
)
PRIVATE_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260909T090428Z-a5968591-attempt-001.blind-start-parity.jsonl.xz"
)
CASH_OUT_FIXTURE = (
    FIXTURE_ROOT
    / "balatro-20260909T090428Z-a5968591-attempt-001.cash-out.jsonl.xz"
)
_PUBLIC_SHA256 = "1c3823b66bbbc3559332f8f38369507483edec8d49c00007929064c307ad7d64"
_PRIVATE_SHA256 = "f353095e5cd93caee6a82e3ea85b848e7a5f7a14df95fe49d9ea8f21cb81feb5"
_CASH_OUT_SHA256 = "f77b50b0152d4f9a3a6fbb0969e3cf4e4e8d199c90ff1a260f1bf1e0cd7095e8"


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


def test_env_r5_real_small_blind_fixture_fails_closed_without_facing_authority():
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

    assert all(not card.facing_observed for card in live[0].after.hand)
    assert all(card.facing_observed for card in comparison.simulator_evidence.after.hand)
    assert comparison.matches is False
    assert comparison.differences == ("public.after",)
    assert comparison.public.matches is False
    assert comparison.public.differences == ("after",)


def test_env_r5_real_small_blind_fixture_preserves_authoritative_owned_deck_composition():
    public_rows = _fixture_rows(PUBLIC_FIXTURE)
    live = successful_select_blind_evidence_from_run_rows(public_rows)

    assert len(live) == 1
    owned_deck = live[0].before.owned_deck

    assert owned_deck is not None
    assert len(owned_deck) == 52
    assert all(type(card.live_id) is int and card.live_id >= 0 for card in owned_deck)
    assert len({card.live_id for card in owned_deck}) == 52

    expected_identities = {
        (rank, suit)
        for rank in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
        for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
    }
    assert {(card.rank, card.suit) for card in owned_deck} == expected_identities


def test_env_r5_real_small_blind_cashout_replays_unchanged_through_exact_owner():
    cash_out_raw = _fixture_bytes(CASH_OUT_FIXTURE)
    rows = _fixture_rows(CASH_OUT_FIXTURE)
    private_row = _fixture_rows(PRIVATE_FIXTURE)[0]

    assert hashlib.sha256(cash_out_raw).hexdigest() == _CASH_OUT_SHA256
    assert [row["sequence"] for row in rows] == [11, 12, 13]
    assert [row["event"] for row in rows] == [
        "observation",
        "decision",
        "action_result",
    ]
    assert rows[1]["data"]["action"] == {"name": "END_ROUND"}
    assert rows[2]["data"]["action"] == {"name": "END_ROUND"}
    assert rows[2]["data"]["success"] is True

    translator = DefaultBalatroStateTranslator()
    before = translator.translate(_snapshot_from_log_state(rows[0]["data"]["state"]))
    live_after = translator.translate(
        _snapshot_from_log_state(rows[2]["data"]["state"])
    )

    # At ROUND_EVAL vanilla has already repopulated G.deck. Physical order is
    # hidden, but cash_out pseudoshuffle first sorts by creation order, so the
    # exact complete live-id collection is sufficient replay authority.
    owned_by_id = {card.live_id: card for card in before.owned_deck or ()}
    assert len(owned_by_id) == len(before.deck) == 52
    before.deck = [owned_by_id[card.live_id] for card in before.deck]
    after_blind_start = blind_start_parity_checkpoint_from_payload(
        private_row["after"]
    )
    run = HeadlessRunState(
        public=before,
        seed=after_blind_start.rng_snapshot["seed"],
        rng_state=after_blind_start.rng_snapshot,
        draw_pile=list(before.deck),
    )

    result = cash_out_baseline_ordinary_blind(run)

    assert canonical_public_state_signature(result.public) == (
        canonical_public_state_signature(live_after)
    )
    assert "cashout1" in result.rng_snapshot()["nodes"]
