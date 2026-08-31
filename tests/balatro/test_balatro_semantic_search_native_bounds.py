from types import SimpleNamespace

import games.balatro  # noqa: F401 - initialize production registration
from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.bonds.behavior_strategy import _Node, _relation
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


def _card(rank="2"):
    return SimpleNamespace(
        rank=rank,
        suit="Clubs",
        enhancement=None,
        edition=None,
        seal=None,
        debuffed=False,
    )


def test_behavior_rank_guard_is_native_to_relation():
    rank_feature = _Node(
        source="feature:rank:2",
        bond_ids=("low_ranks",),
        outputs=frozenset({"rank:2"}),
        requires=frozenset(),
        scales_with=frozenset(),
        amplifies=frozenset(),
        value=1.0,
    )
    broad_requirement = _Node(
        source="scenario:broad-rank-payoff",
        bond_ids=("rank_payoff",),
        outputs=frozenset(),
        requires=frozenset({f"rank:{rank}" for rank in ("2", "3", "4", "5", "6", "7")}),
        scales_with=frozenset(),
        amplifies=frozenset(),
        value=1.0,
    )

    assert _relation(rank_feature, broad_requirement) is None


def test_native_discard_prefilter_preserves_wide_redraw_branch():
    planner = LiveBlindClearPlanner()
    cards = [_card(str(rank)) for rank in range(2, 7)]
    singleton_a = BalatroAction(DISCARD_CARDS, cards=[cards[0]])
    singleton_b = BalatroAction(DISCARD_CARDS, cards=[cards[1]])
    singleton_c = BalatroAction(DISCARD_CARDS, cards=[cards[2]])
    wide = BalatroAction(DISCARD_CARDS, cards=cards[:4])
    priorities = {
        id(singleton_a): (100.0, 1),
        id(singleton_b): (90.0, 1),
        id(singleton_c): (80.0, 1),
        id(wide): (1.0, 4),
    }
    planner._cheap_discard_key = lambda _state, action: priorities[id(action)]

    chosen = planner._prefilter_discards(
        SimpleNamespace(hand=cards),
        [singleton_a, singleton_b, singleton_c, wide],
        limit=2,
    )

    assert wide in chosen
    assert len(chosen) == 2


def test_native_root_reserve_keeps_discard_evidence_when_only_plays_survive():
    planner = LiveBlindClearPlanner()
    played = _card("A")
    discarded = _card("2")
    play = BalatroAction(PLAY_CARDS, cards=[played])
    discard = BalatroAction(DISCARD_CARDS, cards=[discarded])
    planner.action_generator = SimpleNamespace(
        generate_discard_actions=lambda _state: [discard],
    )
    planner._cheap_discard_key = lambda _state, action: (1.0, len(action.cards))
    state = SimpleNamespace(
        hand=[played, discarded],
        discards_remaining=1,
        boss_name="",
        jokers=[],
    )

    chosen = planner._ensure_root_discard_reserve(
        state,
        [play],
        allow_discards=True,
        discard_limit=2,
    )

    assert play in chosen
    assert discard in chosen


def test_production_stack_does_not_replace_native_candidate_generation():
    assert LiveBlindClearPlanner._candidate_actions.__module__ == (
        "games.balatro.live.blind_clear_planner"
    )
