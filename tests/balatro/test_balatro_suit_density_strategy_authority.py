from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.model import BondRank
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.state import BalatroState


def _concentrated_hearts_state() -> BalatroState:
    state = BalatroState()
    deck = list(state.deck)
    hearts = [card for card in deck if str(getattr(card, "suit", "")).lower() == "hearts"]
    non_hearts = [card for card in deck if str(getattr(card, "suit", "")).lower() != "hearts"]

    # Preserve a 52-card public deck while creating enough permanent Hearts density
    # to cross the current Hearts R1 threshold without introducing any payoff Joker.
    # Reusing modeled card objects is sufficient here because Bond evaluation reads
    # permanent public composition only; no draw-order or mutation semantics matter.
    concentrated = (hearts + hearts[:8] + non_hearts)[:52]
    assert sum(1 for card in concentrated if str(getattr(card, "suit", "")).lower() == "hearts") == 21

    state.owned_deck = concentrated
    return state


def _candidate_mentions(candidate, bond_id: str) -> bool:
    return bond_id in set(getattr(candidate, "bond_ids", ()) or ())


def test_natural_suit_density_does_not_create_strategy_authority():
    state = BalatroState()
    state.owned_deck = list(state.deck)

    developments, composition = evaluate_bond_composition(state)
    hearts = next(dev for dev in developments if dev.bond_id == "hearts")

    assert hearts.rank == BondRank.R0
    assert not any(
        _candidate_mentions(candidate, "hearts")
        and candidate.commitment >= StrategyCommitment.FORMING
        for candidate in composition.strategy_candidates
    )
    assert composition.pinned_strategy_id is None


def test_r1_density_only_suit_bond_still_cannot_form_strategy():
    developments, composition = evaluate_bond_composition(_concentrated_hearts_state())
    hearts = next(dev for dev in developments if dev.bond_id == "hearts")

    # R1 is legitimate structural development: the permanent deck really is
    # Hearts-concentrated. But density infrastructure by itself is not a scoring
    # engine and must not receive FORMING/PINNED authority without payoff semantics.
    assert hearts.rank >= BondRank.R1
    assert not any(
        _candidate_mentions(candidate, "hearts")
        and candidate.commitment >= StrategyCommitment.FORMING
        for candidate in composition.strategy_candidates
    )
    assert composition.pinned_strategy_id is None
