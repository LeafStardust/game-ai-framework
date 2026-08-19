from __future__ import annotations

from dataclasses import dataclass

import pytest

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER
from games.balatro.card import BalatroCard
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.pack import LivePackChoice
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.external.live_memory_pack_terms import LivePackSelectionTerms
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.state import BalatroState


class _Translator:
    def __init__(self, state: BalatroState):
        self.state = state

    def translate(self, snapshot: LiveBalatroSnapshot) -> BalatroState:
        return self.state


class _Observer:
    def __init__(self, *snapshots: LiveBalatroSnapshot):
        self.snapshots = list(snapshots)
        self.last = snapshots[-1]

    def observe(self) -> LiveBalatroSnapshot:
        if self.snapshots:
            self.last = self.snapshots.pop(0)
        return self.last


class _Bridge:
    def __init__(self):
        self.calls: list[tuple[str, tuple[int, ...]]] = []
        self.status_calls = 0

    def status(self):
        self.status_calls += 1
        return {
            "bridge": "1",
            "achievement_gate": "ENABLED",
            "bridge_revision": "test",
        }

    def select_pack_card(self, index: int, target_indices=()):
        self.calls.append(("PACK_SELECT", (index, *tuple(target_indices))))
        return "accepted"

    def skip_booster(self):
        self.calls.append(("PACK_SKIP", ()))
        return "accepted"


class _PositiveEstimator:
    def estimate(self, state, action):
        return 1.0, ("fixture positive item value",)


@dataclass(frozen=True)
class _FamilyCase:
    phase: str
    choice: LivePackChoice
    state: BalatroState
    after_payload: dict


def _snapshot(
    sequence: int,
    phase: str,
    *,
    payload: dict | None = None,
) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload=payload or {},
    )


def _raw_card(
    live_id: int,
    rank: str,
    suit: str,
    *,
    enhancement=None,
    edition=None,
    seal=None,
):
    modifier = {}
    if enhancement is not None:
        modifier["enhancement"] = enhancement
    if edition is not None:
        modifier["edition"] = edition
    if seal is not None:
        modifier["seal"] = seal
    return {
        "live_id": live_id,
        "value": {"rank": rank, "suit": suit},
        "modifier": modifier,
    }


def _choice(
    phase: str,
    kind: str,
    label: str | None,
    *,
    address: int,
    live_id: int,
    value: dict | None = None,
    modifier: dict | None = None,
) -> LivePackChoice:
    data = {
        "area_index": 0,
        "address": address,
        "live_id": live_id,
        "label": label,
        "ability_name": label,
        "ability_set": kind,
        "center": f"fixture_{phase.lower()}_{live_id}",
    }
    if value is not None:
        data["value"] = value
    if modifier is not None:
        data["modifier"] = modifier
    return LivePackChoice(area_index=0, address=address, data=data)


def _state(phase: str) -> BalatroState:
    state = BalatroState()
    state.phase = phase
    state.joker_slots = 5
    return state


def _runner(
    *,
    before: LiveBalatroSnapshot,
    after_snapshots: tuple[LiveBalatroSnapshot, ...],
    state: BalatroState,
    choice: LivePackChoice,
    pack_policy: BalatroPackPolicy | None = None,
):
    # decide() consumes the first checkpoint; execute() independently verifies the
    # same public checkpoint before and after STATUS, then the real dispatcher owns
    # all subsequent observations until its semantic postcondition is satisfied.
    observer = _Observer(before, before, before, *after_snapshots)
    bridge = _Bridge()
    terms = LivePackSelectionTerms(
        choices_remaining=1,
        choice_addresses=(choice.address,),
    )
    dispatcher = LiveMemoryInjectedActionDispatcher(
        observer,
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
        pack_terms_reader=lambda: terms,
    )
    runner = LiveMemoryInjectedSingleStepRunner(
        observer,
        translator=_Translator(state),
        bridge=bridge,
        dispatcher=dispatcher,
        pack_choice_reader=lambda: (choice,),
    )
    if pack_policy is not None:
        runner.pack_policy = pack_policy
    return runner, bridge


def _family_cases() -> tuple[_FamilyCase, ...]:
    buffoon_state = _state("BUFFOON_PACK")
    buffoon = _choice(
        "BUFFOON_PACK",
        "Joker",
        "Golden Joker",
        address=0x1001,
        live_id=501,
    )

    standard_state = _state("STANDARD_PACK")
    standard_state.deck = [BalatroCard("Q", "Hearts") for _ in range(8)]
    standard = _choice(
        "STANDARD_PACK",
        "PLAYING_CARD",
        "Steel King",
        address=0x1002,
        live_id=502,
        value={"rank": "K", "suit": "Hearts"},
        modifier={"enhancement": "m_steel"},
    )

    planet_state = _state("PLANET_PACK")
    planet_state.hand_levels["PAIR"] = 3
    planet = _choice(
        "PLANET_PACK",
        "Planet",
        "Mercury",
        address=0x1003,
        live_id=503,
    )

    tarot_state = _state("TAROT_PACK")
    tarot_state.money = 10
    tarot = _choice(
        "TAROT_PACK",
        "Tarot",
        "The Hermit",
        address=0x1004,
        live_id=504,
    )

    spectral_state = _state("SPECTRAL_PACK")
    spectral = _choice(
        "SPECTRAL_PACK",
        "Spectral",
        "Black Hole",
        address=0x1005,
        live_id=505,
    )

    return (
        _FamilyCase("BUFFOON_PACK", buffoon, buffoon_state, {}),
        _FamilyCase(
            "STANDARD_PACK",
            standard,
            standard_state,
            {
                "owned_cards": {
                    "cards": [
                        _raw_card(9001, "K", "Hearts", enhancement="m_steel")
                    ]
                }
            },
        ),
        _FamilyCase("PLANET_PACK", planet, planet_state, {}),
        _FamilyCase("TAROT_PACK", tarot, tarot_state, {}),
        _FamilyCase("SPECTRAL_PACK", spectral, spectral_state, {}),
    )


@pytest.mark.parametrize("case", _family_cases(), ids=lambda case: case.phase)
def test_d9_recommendation_reaches_injected_selection_and_authoritative_checkpoint(
    case: _FamilyCase,
):
    before_payload = {"owned_cards": {"cards": []}} if case.phase == "STANDARD_PACK" else {}
    before = _snapshot(10, case.phase, payload=before_payload)
    after = _snapshot(11, "SHOP", payload=case.after_payload)
    runner, bridge = _runner(
        before=before,
        after_snapshots=(after,),
        state=case.state,
        choice=case.choice,
    )

    decision = runner.decide()
    result, status = runner.execute(decision)

    assert decision.source == "pack policy"
    assert decision.action.name == SELECT_PACK_CARD
    assert decision.action.target is case.choice
    assert result.before is before
    assert result.after is after
    assert bridge.calls == [("PACK_SELECT", (0,))]
    assert bridge.status_calls == 1
    assert status["achievement_gate"] == "ENABLED"
    assert result.details["area_index"] == 0
    assert result.details["selected_address"] == case.choice.address


def test_d9_skip_recommendation_reaches_injected_skip_and_terminal_checkpoint():
    state = _state("STANDARD_PACK")
    choice = _choice(
        "STANDARD_PACK",
        "PLAYING_CARD",
        "Vanilla Two",
        address=0x2001,
        live_id=601,
        value={"rank": "2", "suit": "Hearts"},
        modifier={},
    )
    before = _snapshot(20, "STANDARD_PACK")
    after = _snapshot(21, "SHOP")
    runner, bridge = _runner(
        before=before,
        after_snapshots=(after,),
        state=state,
        choice=choice,
    )

    decision = runner.decide()
    result, _ = runner.execute(decision)

    assert decision.action.name == SKIP_BOOSTER
    assert result.after is after
    assert bridge.calls == [("PACK_SKIP", ())]


@pytest.mark.parametrize(
    ("phase", "kind", "label", "after_card", "expected_detail"),
    (
        (
            "TAROT_PACK",
            "Tarot",
            "The Chariot",
            _raw_card(101, "4", "Clubs", enhancement="m_steel"),
            (101,),
        ),
        (
            "SPECTRAL_PACK",
            "Spectral",
            "Deja Vu",
            _raw_card(101, "4", "Clubs", seal="RED"),
            (101,),
        ),
    ),
)
def test_d10_target_recommendation_is_verified_after_injected_pack_use(
    phase: str,
    kind: str,
    label: str,
    after_card: dict,
    expected_detail: tuple[int, ...],
):
    card = BalatroCard("4", "Clubs", live_id=101)
    state = _state(phase)
    state.hand = [card]
    state.deck = [BalatroCard("4", "Clubs")]
    choice = _choice(
        phase,
        kind,
        label,
        address=0x3001,
        live_id=701,
    )
    before = _snapshot(
        30,
        phase,
        payload={"owned_cards": {"cards": [_raw_card(101, "4", "Clubs")]}}
    )
    unresolved = _snapshot(
        31,
        "SHOP",
        payload={"owned_cards": {"cards": [_raw_card(101, "4", "Clubs")]}}
    )
    settled = _snapshot(
        32,
        "SHOP",
        payload={"owned_cards": {"cards": [after_card]}}
    )
    runner, bridge = _runner(
        before=before,
        after_snapshots=(unresolved, settled),
        state=state,
        choice=choice,
        pack_policy=BalatroPackPolicy(
            item_estimator=_PositiveEstimator(),
            skip_bias=0.35,
        ),
    )

    decision = runner.decide()
    result, _ = runner.execute(decision)

    assert decision.action.name == SELECT_PACK_CARD
    assert decision.action.cards == [card]
    assert bridge.calls == [("PACK_SELECT", (0, 0))]
    assert result.after is settled
    assert result.details["target_indices"] == (0,)
    assert result.details["verified_target_live_ids"] == expected_detail
