from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

import games.balatro.boss_hand_constraint_policy as module
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS


class _Policy:
    def _structure_fit(self, cards, target_hand, *, rules=None):
        del rules
        assert target_hand == "FULL HOUSE"
        counts = sorted(Counter(card.rank for card in cards).values(), reverse=True)
        first = counts[0] if counts else 0
        second = counts[1] if len(counts) > 1 else 0
        return 0.6 * min(1.0, first / 3.0) + 0.4 * min(1.0, second / 2.0)


def _card(rank: str):
    return SimpleNamespace(rank=rank)


def _play(*cards, hand_type="HIGH CARD"):
    return SimpleNamespace(
        action=SimpleNamespace(name=PLAY_CARDS, cards=tuple(cards)),
        hand_type=hand_type,
    )


def _discard(*cards):
    return SimpleNamespace(
        action=SimpleNamespace(name=DISCARD_CARDS, cards=tuple(cards)),
        hand_type=None,
    )


def test_mouth_without_discards_uses_widest_play_that_preserves_best_structure(monkeypatch):
    pair_a = _card("6")
    pair_b = _card("6")
    dead = [_card(rank) for rank in ("A", "K", "Q", "J", "9")]
    state = SimpleNamespace(hand=(pair_a, pair_b, *dead), discards_remaining=0)

    singleton = _play(dead[0])
    wide_preserving = _play(*dead[:4])
    overwide_loses_structure = _play(*dead)
    breaks_pair = _play(pair_a, *dead[:3])
    supplied = (singleton, wide_preserving, overwide_loses_structure, breaks_pair)

    monkeypatch.setattr(module, "_mouth_locked_hand", lambda state: "FULL HOUSE")
    monkeypatch.setattr(module, "_hand_type", lambda policy, state, plan: plan.hand_type)

    constrained = module._mouth_filter(_Policy(), state, supplied)

    assert constrained == (wide_preserving,)
    assert pair_a not in wide_preserving.action.cards
    assert pair_b not in wide_preserving.action.cards
    assert dead[4] not in wide_preserving.action.cards
    assert len(wide_preserving.action.cards) == 4


def test_mouth_matching_scoring_play_remains_authoritative(monkeypatch):
    cards = tuple(_card(rank) for rank in ("6", "6", "6", "K", "K", "A"))
    state = SimpleNamespace(hand=cards, discards_remaining=0)
    matching = _play(*cards[:5], hand_type="FULL HOUSE")
    off_type_wide = _play(*cards[1:6], hand_type="HIGH CARD")

    monkeypatch.setattr(module, "_mouth_locked_hand", lambda state: "FULL HOUSE")
    monkeypatch.setattr(module, "_hand_type", lambda policy, state, plan: plan.hand_type)

    constrained = module._mouth_filter(_Policy(), state, (off_type_wide, matching))

    assert constrained == (matching,)


def test_mouth_real_discard_still_precedes_zero_score_play_recovery(monkeypatch):
    cards = tuple(_card(rank) for rank in ("6", "6", "A", "K", "Q", "J", "9"))
    state = SimpleNamespace(hand=cards, discards_remaining=1)
    off_type = _play(*cards[2:7], hand_type="HIGH CARD")
    discard = _discard(*cards[2:7])

    monkeypatch.setattr(module, "_mouth_locked_hand", lambda state: "FULL HOUSE")
    monkeypatch.setattr(module, "_hand_type", lambda policy, state, plan: plan.hand_type)

    constrained = module._mouth_filter(_Policy(), state, (off_type, discard))

    assert constrained == (discard,)
