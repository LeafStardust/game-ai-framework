from __future__ import annotations

"""Realized Build Health coverage for non-Bond persistent scalers.

Some scalable Jokers intentionally remain outside the Bond catalogue because they
are tactical/support or composer-level mechanics rather than independent persistent
Bond axes. That does not make their already-realized public scaling state invisible
to Build Health.
"""

from games.balatro.build_health import EngineState, RealizedEngineStrength
from games.balatro.build_health_runtime import RealizedEngineAnalyzer


def _normalize(value: object) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    for value in (getattr(joker, "name", None), getattr(joker, "label", None), getattr(joker, "ability_name", None), type(joker).__name__):
        token = _normalize(value)
        if token:
            return token
    return ""


def _number(joker: object, field: str, default: float) -> float:
    try:
        return float(getattr(joker, field, default))
    except (TypeError, ValueError):
        return float(default)


def _state_from_progress(progress: float) -> EngineState:
    progress = max(0.0, float(progress))
    if progress <= 0.0:
        return EngineState.OWNED_INACTIVE
    if progress < 0.50:
        return EngineState.ACTIVATED_WEAK
    if progress < 1.50:
        return EngineState.ACTIVATED_HEALTHY
    return EngineState.MATURE


def _runway_need(state: EngineState, *, brittle: bool = False) -> float:
    base = {
        EngineState.NOT_OWNED: 0.0,
        EngineState.OWNED_INACTIVE: 0.75,
        EngineState.ACTIVATED_WEAK: 0.55,
        EngineState.ACTIVATED_HEALTHY: 0.25,
        EngineState.MATURE: 0.05,
    }[state]
    return min(1.0, base + (0.15 if brittle and state != EngineState.MATURE else 0.0))


def _owned_deck(state) -> tuple[object, ...]:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return tuple(owned)
    return tuple(getattr(state, "deck", ()) or ())


def _tactical_scaler_engines(state) -> tuple[RealizedEngineStrength, ...]:
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    jokers = tuple(getattr(state, "jokers", ()) or ())
    tokenized = tuple((_joker_token(joker), joker) for joker in jokers)
    engines: list[RealizedEngineStrength] = []

    campfires = tuple(joker for token, joker in tokenized if token in {"campfire", "campfirejoker"})
    if campfires:
        x_mults = tuple(max(1.0, _number(joker, "x_mult", 1.0)) for joker in campfires)
        realized_gain = sum(max(0.0, value - 1.0) for value in x_mults)
        target_gain = max(0.50, 0.25 * max(2, ante)) * len(campfires)
        engine_state = _state_from_progress(realized_gain / target_gain)
        engines.append(RealizedEngineStrength(
            engine_id="campfire", state=engine_state, current_strength=float(realized_gain), growth_rate=0.50,
            runway_need=_runway_need(engine_state, brittle=True),
            rationale=(f"Campfire copies={len(campfires)}; public xMult=" + ", ".join(f"x{value:.2f}" for value in x_mults), f"aggregate realized xMult gain={realized_gain:.2f}; Ante {ante} cycle target={target_gain:.2f}", "Campfire growth requires selling and resets after each Boss Blind"),
        ))

    flash_cards = tuple(joker for token, joker in tokenized if token in {"flashcard", "flashcardjoker"})
    if flash_cards:
        mult = sum(max(0.0, _number(joker, "mult", 0.0)) for joker in flash_cards)
        target_mult = max(4.0, float(ante * 2)) * len(flash_cards)
        engine_state = _state_from_progress(mult / target_mult)
        money = max(0, int(getattr(state, "money", 0) or 0))
        growth_rate = 0.60 if money >= 15 else 0.35 if money >= 8 else 0.15
        engines.append(RealizedEngineStrength(
            engine_id="flash_card", state=engine_state, current_strength=float(mult), growth_rate=growth_rate,
            runway_need=_runway_need(engine_state),
            rationale=(f"Flash Card copies={len(flash_cards)}; aggregate public Mult=+{mult:.0f}", f"aggregate realized Ante {ante} target=+{target_mult:.0f} Mult", f"cash=${money}; future growth consumes reroll economy"),
        ))

    obelisks = tuple(joker for token, joker in tokenized if token in {"obelisk", "obeliskjoker"})
    if obelisks:
        x_mults = tuple(max(1.0, _number(joker, "x_mult", 1.0)) for joker in obelisks)
        realized_gain = sum(max(0.0, value - 1.0) for value in x_mults)
        target_gain = max(0.40, 0.20 * max(2, ante)) * len(obelisks)
        engine_state = _state_from_progress(realized_gain / target_gain)
        engines.append(RealizedEngineStrength(
            engine_id="obelisk", state=engine_state, current_strength=float(realized_gain), growth_rate=0.40,
            runway_need=_runway_need(engine_state, brittle=True),
            rationale=(f"Obelisk copies={len(obelisks)}; public xMult=" + ", ".join(f"x{value:.2f}" for value in x_mults), f"aggregate realized xMult gain={realized_gain:.2f}; Ante {ante} target={target_gain:.2f}", "Obelisk resets when the most-played hand is used"),
        ))

    # Red Card is deliberately not a Bond, but its +Mult accumulated from skipped
    # booster packs is persistent realized power and must not disappear from health
    # merely because its strategy classification is tactical/support.
    red_cards = tuple(joker for token, joker in tokenized if token in {"redcard", "redcardjoker"})
    if red_cards:
        mult = sum(max(0.0, _number(joker, "mult", 0.0)) for joker in red_cards)
        target_mult = max(6.0, float(ante * 3)) * len(red_cards)
        engine_state = _state_from_progress(mult / target_mult)
        engines.append(RealizedEngineStrength(
            engine_id="red_card", state=engine_state, current_strength=float(mult), growth_rate=0.45,
            runway_need=_runway_need(engine_state),
            rationale=(f"Red Card copies={len(red_cards)}; aggregate public Mult=+{mult:.0f}", f"aggregate realized Ante {ante} target=+{target_mult:.0f} Mult", "future booster skips are not pre-credited as realized strength"),
        ))

    hikers = tuple(joker for token, joker in tokenized if token in {"hiker", "hikerjoker"})
    if hikers:
        deck = _owned_deck(state)
        bonuses = tuple(max(0, int(getattr(card, "permanent_bonus", 0) or 0)) for card in deck)
        total_bonus = sum(bonuses)
        trained_cards = sum(1 for bonus in bonuses if bonus > 0)
        target_bonus = max(20.0, float(ante * 10))
        engine_state = _state_from_progress(total_bonus / target_bonus)
        growth_rate = min(1.0, 0.50 + 0.20 * max(0, len(hikers) - 1))
        engines.append(RealizedEngineStrength(
            engine_id="hiker_card_growth", state=engine_state, current_strength=float(total_bonus), growth_rate=growth_rate,
            runway_need=_runway_need(engine_state),
            rationale=(f"Hiker copies={len(hikers)}; trained permanent cards={trained_cards}/{len(deck)}", f"aggregate public permanent chip bonus=+{total_bonus}; Ante {ante} target=+{target_bonus:.0f}", "only already-written permanent card bonuses count as realized Hiker strength"),
        ))

    return tuple(engines)


def install_tactical_scaler_build_health_policy() -> None:
    if getattr(RealizedEngineAnalyzer, "_tactical_scaler_health_installed", False):
        return
    original_analyze = RealizedEngineAnalyzer.analyze

    def analyze(self, state):
        existing = tuple(original_analyze(self, state))
        existing_ids = {engine.engine_id for engine in existing}
        additions = tuple(engine for engine in _tactical_scaler_engines(state) if engine.engine_id not in existing_ids)
        return (*existing, *additions)

    RealizedEngineAnalyzer.analyze = analyze
    RealizedEngineAnalyzer._tactical_scaler_health_installed = True
