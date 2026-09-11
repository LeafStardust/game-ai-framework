from copy import deepcopy

import pytest

from games.balatro.actions import SELECT_BLIND
from games.balatro.env.actions import EnvAction
from games.balatro.env.rng import pseudohash
from games.balatro.env.strategic_evidence import (
    build_public_strategic_transition_evidence,
    select_blind_with_public_evidence,
)
from games.balatro.live.blind_start_parity_checkpoint import (
    LiveBlindStartParityCheckpoint,
    LiveBlindStartParityCheckpointError,
    capture_live_blind_start_parity_checkpoint,
    compare_live_blind_start_replay,
    headless_blind_start_run_from_live_checkpoint,
)
from games.balatro.live.parity_capture import (
    successful_select_blind_evidence_from_run_rows,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.luajit_memory import LuaValue


RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
SUITS = ("C", "D", "H", "S")


def _card(card_id, rank, suit):
    return {
        "live_id": card_id,
        "value": {"rank": rank, "suit": suit},
        "played_this_ante_observed": True,
        "played_this_ante": False,
    }


def _base_cards():
    return [
        _card(index, rank, suit)
        for index, (suit, rank) in enumerate(
            ((suit, rank) for suit in SUITS for rank in RANKS),
            start=1,
        )
    ]


def _snapshot(
    *,
    sequence=1,
    phase="BLIND_SELECT",
    cards=None,
    boss_name=None,
    requirement=300,
):
    cards = deepcopy(_base_cards() if cards is None else cards)
    payload = {
        "deck": "RED",
        "stake": "WHITE",
        "ante_num": 1,
        "round_num": 0 if phase == "BLIND_SELECT" else 1,
        "money": 4,
        "score": 0,
        "round": {"hands_left": 4, "discards_left": 3, "chips": requirement},
        "round_reset_hands_observed": True,
        "round_reset_hands": 4,
        "round_reset_discards_observed": True,
        "round_reset_discards": 3,
        "hand": {"limit": 8, "cards": []},
        "cards": {"cards": cards},
        "owned_cards": {"count": len(cards), "cards": deepcopy(cards)},
        "jokers": {"limit": 5, "count": 0, "cards": []},
        "consumables": {"limit": 2, "cards": []},
        "vouchers_observed": True,
        "vouchers": [],
        "blinds": {
            "boss" if boss_name else "small": {
                "type": "BOSS" if boss_name else "SMALL",
                "status": "SELECT" if phase == "BLIND_SELECT" else "CURRENT",
                "score": requirement,
                "reward": 5 if boss_name else 3,
                **(
                    {"name": boss_name, "key": "bl_tooth"}
                    if boss_name
                    else {}
                ),
            }
        },
    }
    return LiveBalatroSnapshot(sequence, phase, True, payload)


def _lua(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


class _Decoder:
    def __init__(self, tags=0, draw_ids=range(1, 53)):
        seed = "R5-BLIND-START"
        deck = 500
        deck_cards = 501
        draw_ids = tuple(draw_ids)
        self.tables = {
            100: {
                "pseudorandom": _lua("table", 200),
                "tags": _lua("table", 300),
            },
            200: {
                "seed": _lua("string", seed),
                "hashed_seed": _lua("number", pseudohash(seed)),
            },
            deck: {"cards": _lua("table", deck_cards)},
        }
        self.tables.update(
            {
                600 + index: {"playing_card": _lua("number", live_id)}
                for index, live_id in enumerate(draw_ids)
            }
        )
        self.arrays = {
            300: [
                (index + 1, _lua("table", 400 + index))
                for index in range(tags)
            ],
            deck_cards: [
                (index + 1, _lua("table", 600 + index))
                for index in range(len(draw_ids))
            ],
        }

    def string_fields(self, address):
        return dict(self.tables[address])

    def array_items(self, address):
        return list(self.arrays.get(address, ()))

    def array_items_strict(self, address):
        return list(self.arrays.get(address, ()))


class _Observer:
    def __init__(self, snapshots, *, tags=0):
        self.snapshots = list(snapshots)
        self.decoder = _Decoder(tags=tags)
        self.calls = 0

    def observe(self):
        index = min(self.calls, len(self.snapshots) - 1)
        self.calls += 1
        return deepcopy(self.snapshots[index])

    def _root(self):
        return self.decoder, 0, {
            "GAME": _lua("table", 100),
            "deck": _lua("table", 500),
        }


def _checkpoint(snapshot, *, tags=0):
    observer = _Observer((snapshot, snapshot), tags=tags)
    return capture_live_blind_start_parity_checkpoint(
        observer,
        expected_phase=snapshot.phase,
    )


def _log_state(snapshot):
    return {
        "sequence": snapshot.sequence,
        "phase": snapshot.phase,
        "state_complete": snapshot.state_complete,
        "payload": deepcopy(snapshot.payload),
    }


def test_env_r5_blind_start_capture_uses_rng_before_physical_draw_pile_exists():
    checkpoint = _checkpoint(_snapshot())

    assert checkpoint.public_snapshot.phase == "BLIND_SELECT"
    assert checkpoint.rng_snapshot["seed"] == "R5-BLIND-START"
    assert checkpoint.active_tag_count == 0
    assert checkpoint.draw_pile_live_ids is None


def test_env_r5_blind_start_capture_reads_exact_post_deal_draw_order():
    checkpoint = _checkpoint(_snapshot(phase="SELECTING_HAND"))

    assert checkpoint.draw_pile_live_ids == tuple(range(1, 53))


def test_env_r5_blind_start_capture_rejects_public_drift():
    observer = _Observer((_snapshot(sequence=1), _snapshot(sequence=2)))

    with pytest.raises(LiveBlindStartParityCheckpointError, match="public state changed"):
        capture_live_blind_start_parity_checkpoint(
            observer,
            expected_phase="BLIND_SELECT",
        )


def test_env_r5_blind_start_restore_rebinds_exact_live_ids_and_rejects_tags():
    checkpoint = _checkpoint(_snapshot())
    run = headless_blind_start_run_from_live_checkpoint(checkpoint)

    assert run.playing_card_order is not None
    assert [card.live_id for card in run.playing_card_order] == list(range(1, 53))
    assert {id(card) for card in run.public.deck} == {
        id(card) for card in run.public.owned_deck
    }

    tagged = LiveBlindStartParityCheckpoint(
        checkpoint.public_snapshot,
        checkpoint.rng_snapshot,
        active_tag_count=1,
    )
    with pytest.raises(LiveBlindStartParityCheckpointError, match="active Tags"):
        headless_blind_start_run_from_live_checkpoint(tagged)


def test_env_r5_blind_start_restore_normalizes_live_numeric_deck_ids():
    snapshot = _snapshot()
    for area in ("cards", "owned_cards"):
        for card in snapshot.payload[area]["cards"]:
            card["live_id"] = float(card["live_id"])

    run = headless_blind_start_run_from_live_checkpoint(_checkpoint(snapshot))

    assert [card.live_id for card in run.public.deck] == list(range(1, 53))
    assert all(type(card.live_id) is int for card in run.public.deck)
    assert {id(card) for card in run.public.deck} == {
        id(card) for card in run.public.owned_deck
    }


def test_env_r5_blind_start_restore_rejects_mismatched_permanent_ids():
    snapshot = _snapshot()
    snapshot.payload["owned_cards"]["cards"][0]["live_id"] = 999
    checkpoint = _checkpoint(snapshot)

    with pytest.raises(LiveBlindStartParityCheckpointError, match="deck IDs"):
        headless_blind_start_run_from_live_checkpoint(checkpoint)


def test_env_r5_blind_start_restore_rejects_private_draw_composition_drift():
    checkpoint = _checkpoint(_snapshot())
    drifted = LiveBlindStartParityCheckpoint(
        public_snapshot=checkpoint.public_snapshot,
        rng_snapshot=checkpoint.rng_snapshot,
        active_tag_count=checkpoint.active_tag_count,
        draw_pile_live_ids=tuple(range(2, 54)),
    )

    with pytest.raises(
        LiveBlindStartParityCheckpointError,
        match="private draw pile does not match",
    ):
        headless_blind_start_run_from_live_checkpoint(drifted)


def test_env_r5_select_blind_log_mapping_is_parameterless_and_fail_closed():
    before = _snapshot(sequence=10)
    after = _snapshot(sequence=11, phase="SELECTING_HAND", cards=[])
    action = {"name": SELECT_BLIND}
    rows = [
        {"event": "observation", "data": {"state": _log_state(before)}},
        {"event": "decision", "data": {"action": action}},
        {
            "event": "action_result",
            "data": {
                "action": action,
                "success": True,
                "state": _log_state(after),
            },
        },
    ]

    evidence = successful_select_blind_evidence_from_run_rows(rows)
    assert evidence[0].action.alias == "SELECT_BLIND"
    assert evidence[0].action.params == ()

    rows[1]["data"]["action"] = {"name": SELECT_BLIND, "target": {}}
    rows[2]["data"]["action"] = rows[1]["data"]["action"]
    with pytest.raises(ValueError, match="must not contain parameters"):
        successful_select_blind_evidence_from_run_rows(rows)


def test_env_r5_live_id_base_deck_replays_exact_shuffle_and_private_rng():
    before_checkpoint = _checkpoint(_snapshot(sequence=20))
    before_run = headless_blind_start_run_from_live_checkpoint(before_checkpoint)
    result, live_evidence = select_blind_with_public_evidence(before_run)
    after_snapshot = _snapshot(sequence=21, phase="SELECTING_HAND", cards=[])
    after_checkpoint = LiveBlindStartParityCheckpoint(
        public_snapshot=after_snapshot,
        rng_snapshot=result.rng_snapshot(),
        active_tag_count=0,
        draw_pile_live_ids=tuple(card.live_id for card in result.draw_pile),
    )

    class _Translator:
        def translate(self, snapshot):
            if snapshot.phase == "BLIND_SELECT":
                return deepcopy(before_run.public)
            return deepcopy(result.public)

    comparison = compare_live_blind_start_replay(
        before_checkpoint,
        after_checkpoint,
        build_public_strategic_transition_evidence(
            before_run.public,
            live_evidence.action,
            result.public,
        ),
        translator=_Translator(),
    )

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == 8
    assert comparison.matches is True
    assert comparison.differences == ()

    drifted = LiveBlindStartParityCheckpoint(
        public_snapshot=after_snapshot,
        rng_snapshot=result.rng_snapshot(),
        active_tag_count=0,
        draw_pile_live_ids=tuple(
            reversed(tuple(card.live_id for card in result.draw_pile))
        ),
    )
    mismatch = compare_live_blind_start_replay(
        before_checkpoint,
        drifted,
        build_public_strategic_transition_evidence(
            before_run.public,
            live_evidence.action,
            result.public,
        ),
        translator=_Translator(),
    )
    assert mismatch.matches is False
    assert mismatch.differences == ("draw_pile.after",)


def test_env_r5_blind_start_checkpoint_replays_exact_start_inert_tooth_boss():
    before = _checkpoint(
        _snapshot(
            sequence=30,
            boss_name="The Tooth",
            requirement=600,
        )
    )

    run = headless_blind_start_run_from_live_checkpoint(before)
    result, evidence = select_blind_with_public_evidence(run)

    assert run.public.boss_name == "The Tooth"
    assert run.public.blind.requirement == 600
    assert result.public.phase == "SELECTING_HAND"
    assert result.public.boss_name == "The Tooth"
    assert result.public.blind.requirement == 600
    assert result.public.blind_score == 600
    assert len(result.public.hand) == 8
    assert evidence.action == EnvAction.from_alias("SELECT_BLIND")
