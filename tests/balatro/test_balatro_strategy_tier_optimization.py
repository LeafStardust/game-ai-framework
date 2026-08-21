from games.balatro.strategy import GOLD, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


def _has(bucket, token):
    normalized = "".join(ch for ch in token.lower() if ch.isalnum())
    return normalized in bucket or f"{normalized}joker" in bucket


def test_low_rank_hack_remains_gold_and_fibonacci_is_support():
    strategy = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["low_rank"]

    assert _has(strategy.gold_jokers, "Hack")
    assert not _has(strategy.gold_jokers, "Fibonacci")
    assert _has(strategy.silver_jokers, "Fibonacci")


def test_straight_flush_gold_is_reserved_for_defining_cores():
    strategy = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["straight_flush"]

    for name in ("The Order", "The Tribe", "Runner"):
        assert _has(strategy.gold_jokers, name)

    for name in ("Shortcut", "Four Fingers", "Smeared Joker", "Seance"):
        assert not _has(strategy.gold_jokers, name)
        assert _has(strategy.silver_jokers, name)
