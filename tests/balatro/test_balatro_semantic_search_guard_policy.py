from types import SimpleNamespace

import games.balatro.semantic_search_guard_policy as correction
import games.balatro.strategy_execution_guard_policy as no_discard_policy
from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.bonds.behavior_strategy import _Node


def test_broad_rank_requirement_does_not_form_fake_rank_density_link(monkeypatch):
    original = correction.behavior_strategy._relation
    joker = _Node(
        source="Synthetic hand payoff",
        bond_ids=("three_kind",),
        outputs=frozenset({"score:mult"}),
        requires=frozenset({
            "rank:2", "rank:3", "rank:4", "rank:5", "rank:6", "rank:7",
            "rank:8", "rank:9", "rank:10", "rank:J", "rank:Q", "rank:K", "rank:A",
        }),
        scales_with=frozenset(),
        amplifies=frozenset(),
        value=4.0,
    )
    rank = _Node(
        source="feature:rank:4",
        bond_ids=("low_ranks",),
        outputs=frozenset({"rank:4"}),
        requires=frozenset(),
        scales_with=frozenset(),
        amplifies=frozenset(),
        value=2.0,
    )
    assert original(joker, rank) is None


def test_green_joker_activates_no_discard_execution_immediately(monkeypatch):
    monkeypatch.setattr(
        no_discard_policy,
        "_realized_bond",
        lambda _state, bond_id: bond_id == "no_discard",
    )
    state = SimpleNamespace(jokers=[SimpleNamespace(label="Green Joker")])
    assert no_discard_policy._realized_no_discard_engine(state) is True


def test_delayed_gratification_activates_no_discard_execution_immediately(monkeypatch):
    monkeypatch.setattr(
        no_discard_policy,
        "_realized_bond",
        lambda _state, bond_id: bond_id == "no_discard",
    )
    state = SimpleNamespace(jokers=[SimpleNamespace(label="Delayed Gratification")])
    assert no_discard_policy._realized_no_discard_engine(state) is True


def test_prefilter_bounds_large_root_play_set_without_projecting_every_subset():
    actions = [
        BalatroAction(
            PLAY_CARDS,
            cards=(SimpleNamespace(rank=str((index % 9) + 2), suit="Hearts"),),
        )
        for index in range(64)
    ]
    result = correction._prefilter(
        actions,
        limit=correction._ROOT_PLAY_PREFILTER,
        key=correction._cheap_play_key,
    )
    assert len(result) == correction._ROOT_PLAY_PREFILTER


def test_small_candidate_set_is_not_pruned():
    actions = [
        BalatroAction(PLAY_CARDS, cards=(SimpleNamespace(rank="A", suit="Spades"),)),
        BalatroAction(PLAY_CARDS, cards=(SimpleNamespace(rank="K", suit="Spades"),)),
    ]
    assert correction._prefilter(actions, limit=18, key=correction._cheap_play_key) == actions
