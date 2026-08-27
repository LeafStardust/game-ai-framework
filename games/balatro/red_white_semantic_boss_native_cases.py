from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.boss_blind_integration import boss_play_action_is_legal
from games.balatro.live.hand_action_planner import (
    D1LiveBlindClearPlanner,
    _cerulean_future_forced_branches,
)
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck


def _native_cerulean_mechanics() -> SemanticCheck:
    cards = [SimpleNamespace(live_id=index, forced_selection=False) for index in range(3)]
    state = SimpleNamespace(
        boss_name="Cerulean Bell",
        hand=cards,
        jokers=(),
    )
    cards[1].forced_selection = True
    legal_play = BalatroAction(PLAY_CARDS, cards=[cards[1]])
    illegal_play = BalatroAction(PLAY_CARDS, cards=[cards[0]])
    legal_discard = BalatroAction(DISCARD_CARDS, cards=[cards[1], cards[2]])
    illegal_discard = BalatroAction(DISCARD_CARDS, cards=[cards[0], cards[2]])

    legality = (
        boss_play_action_is_legal(state, legal_play)
        and not boss_play_action_is_legal(state, illegal_play)
        and boss_play_action_is_legal(state, legal_discard)
        and not boss_play_action_is_legal(state, illegal_discard)
    )

    for card in cards:
        card.forced_selection = False
    branches = _cerulean_future_forced_branches(state)
    branch_count = 0 if branches is None else len(branches)
    probability = 0.0 if branches is None else sum(weight for weight, _ in branches)
    one_forced_each = bool(branches) and all(
        sum(bool(getattr(card, "forced_selection", False)) for card in branch.hand) == 1
        for _, branch in branches
    )
    untouched = not any(card.forced_selection for card in state.hand)

    passed = (
        legality
        and branch_count == len(cards)
        and abs(probability - 1.0) <= 1e-12
        and one_forced_each
        and untouched
    )
    return SemanticCheck(
        passed,
        observed=(
            f"legality={legality}, branches={branch_count}, probability={probability:.3f}, "
            f"one_forced_each={one_forced_each}, source_untouched={untouched}"
        ),
        expected="forced card is mandatory for Play/Discard and future Bell selection branches uniformly",
        detail=(
            "Cerulean Bell current legality and next-hand forced-selection projection are "
            "canonical D1 mechanics rather than an installed correction wrapper"
        ),
    )


def _native_serpent_draw_count() -> SemanticCheck:
    planner = object.__new__(D1LiveBlindClearPlanner)
    active = SimpleNamespace(boss_name="The Serpent", jokers=(), hand_size=8)
    ordinary = SimpleNamespace(boss_name="The Ox", jokers=(), hand_size=8)
    retained = [object() for _ in range(2)]

    serpent = planner._post_action_draw_count(active, retained)
    normal = planner._post_action_draw_count(ordinary, retained)
    passed = serpent == 3 and normal == 6
    return SemanticCheck(
        passed,
        observed=f"serpent={serpent}, ordinary={normal}",
        expected="active Serpent draws exactly 3; ordinary replacement draws to hand size",
        detail=(
            "The Serpent draw rule lives directly in canonical D1 successor projection; "
            "no base-planner distribution monkeypatch is required"
        ),
    )


RED_WHITE_BOSS_NATIVE_CASES = (
    SemanticBenchmarkCase(
        case_id="d1.boss.cerulean_native",
        category="D1_SURVIVAL",
        description="Cerulean Bell legality and future forced-card projection are native D1 mechanics",
        evaluate=_native_cerulean_mechanics,
    ),
    SemanticBenchmarkCase(
        case_id="d1.boss.serpent_native",
        category="D1_SURVIVAL",
        description="The Serpent exact three-card redraw is native D1 projection",
        evaluate=_native_serpent_draw_count,
    ),
)