from __future__ import annotations

"""Expose realized public counters of Bond-backed scalers to numeric Build Health.

Canonical Bond development/realization remains authoritative for strategic structure.
The older numeric Build Health still owns a separate Scaling diagnostic used by
several safety-preserving shop policies. It must therefore see already-accumulated
mechanical power from major Bond-backed scalers rather than falling back to the
post-Ante-2 no-engine floor.

This bridge consumes only current public Joker counters. It does not convert Bond
rank/coherence into power and does not credit future triggers as realized strength.
"""

from games.balatro.build_health import EngineState, RealizedEngineStrength
from games.balatro.build_health_runtime import RealizedEngineAnalyzer


def _normalize(value: object) -> str:
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def _token(joker: object) -> str:
    for value in (
        getattr(joker, "name", None),
        getattr(joker, "label", None),
        getattr(joker, "ability_name", None),
        type(joker).__name__,
    ):
        token = _normalize(value)
        if token:
            return token
    return ""


def _number(joker: object, field: str, default: float) -> float:
    try:
        return float(getattr(joker, field, default))
    except (TypeError, ValueError):
        return float(default)


def _progress_state(progress: float) -> EngineState:
    progress = max(0.0, float(progress))
    if progress <= 0.0:
        return EngineState.OWNED_INACTIVE
    if progress < 0.50:
        return EngineState.ACTIVATED_WEAK
    if progress < 1.50:
        return EngineState.ACTIVATED_HEALTHY
    return EngineState.MATURE


def _runway(state: EngineState) -> float:
    return {
        EngineState.NOT_OWNED: 0.0,
        EngineState.OWNED_INACTIVE: 0.75,
        EngineState.ACTIVATED_WEAK: 0.50,
        EngineState.ACTIVATED_HEALTHY: 0.20,
        EngineState.MATURE: 0.0,
    }[state]


def _xmult_engine(
    *,
    engine_id: str,
    jokers: tuple[object, ...],
    ante: int,
    gain_per_step: float,
    growth_rate: float,
    rationale_prefix: str,
) -> RealizedEngineStrength:
    x_mults = tuple(max(1.0, _number(joker, "x_mult", 1.0)) for joker in jokers)
    realized_gain = sum(max(0.0, value - 1.0) for value in x_mults)
    # A healthy route should have accumulated roughly one meaningful growth step
    # per Ante by formation. This is a realized-state yardstick, not future credit.
    target_gain = max(gain_per_step * 2.0, gain_per_step * ante) * len(jokers)
    state = _progress_state(realized_gain / max(target_gain, gain_per_step))
    return RealizedEngineStrength(
        engine_id=engine_id,
        state=state,
        current_strength=realized_gain,
        growth_rate=growth_rate,
        runway_need=_runway(state),
        rationale=(
            f"{rationale_prefix} copies={len(jokers)}; public xMult="
            + ", ".join(f"x{value:.2f}" for value in x_mults),
            f"aggregate realized xMult gain={realized_gain:.2f}; Ante {ante} target={target_gain:.2f}",
            "only current accumulated xMult is counted as realized Build Health strength",
        ),
    )


def _bond_scaler_engines(state) -> tuple[RealizedEngineStrength, ...]:
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    tokenized = tuple((_token(joker), joker) for joker in tuple(getattr(state, "jokers", ()) or ()))

    def find(*tokens: str) -> tuple[object, ...]:
        accepted = set(tokens)
        return tuple(joker for token, joker in tokenized if token in accepted)

    engines: list[RealizedEngineStrength] = []

    constellation = find("constellation", "constellationjoker")
    if constellation:
        engines.append(
            _xmult_engine(
                engine_id="constellation",
                jokers=constellation,
                ante=ante,
                gain_per_step=0.10,
                growth_rate=0.70,
                rationale_prefix="Constellation",
            )
        )

    lucky_cat = find("luckycat", "luckycatjoker")
    if lucky_cat:
        engines.append(
            _xmult_engine(
                engine_id="lucky_cat",
                jokers=lucky_cat,
                ante=ante,
                gain_per_step=0.25,
                growth_rate=0.55,
                rationale_prefix="Lucky Cat",
            )
        )

    glass = find("glassjoker")
    if glass:
        engines.append(
            _xmult_engine(
                engine_id="glass_joker",
                jokers=glass,
                ante=ante,
                gain_per_step=0.75,
                growth_rate=0.40,
                rationale_prefix="Glass Joker",
            )
        )

    vampire = find("vampire", "vampirejoker")
    if vampire:
        engines.append(
            _xmult_engine(
                engine_id="vampire",
                jokers=vampire,
                ante=ante,
                gain_per_step=0.10,
                growth_rate=0.65,
                rationale_prefix="Vampire",
            )
        )

    trousers = find("sparetrousers", "sparetrousersjoker")
    if trousers:
        mult = sum(max(0.0, _number(joker, "mult", 0.0)) for joker in trousers)
        target = max(4.0, float(ante * 2)) * len(trousers)
        engine_state = _progress_state(mult / target)
        engines.append(
            RealizedEngineStrength(
                engine_id="spare_trousers",
                state=engine_state,
                current_strength=mult,
                growth_rate=0.75,
                runway_need=_runway(engine_state),
                rationale=(
                    f"Spare Trousers copies={len(trousers)}; aggregate public Mult=+{mult:.0f}",
                    f"aggregate realized Ante {ante} target=+{target:.0f} Mult",
                    "future Two Pair triggers are not pre-credited as realized strength",
                ),
            )
        )

    wee = find("weejoker")
    if wee:
        chips = sum(max(0.0, _number(joker, "chips", 0.0)) for joker in wee)
        target = max(20.0, float(ante * 20)) * len(wee)
        engine_state = _progress_state(chips / target)
        engines.append(
            RealizedEngineStrength(
                engine_id="wee_joker",
                state=engine_state,
                current_strength=chips,
                growth_rate=0.70,
                runway_need=_runway(engine_state),
                rationale=(
                    f"Wee Joker copies={len(wee)}; aggregate public chips=+{chips:.0f}",
                    f"aggregate realized Ante {ante} target=+{target:.0f} chips",
                    "future scored 2s are not pre-credited as realized strength",
                ),
            )
        )

    return tuple(engines)


def install_bond_scaler_build_health_policy() -> None:
    if getattr(RealizedEngineAnalyzer, "_bond_scaler_health_installed", False):
        return

    original_analyze = RealizedEngineAnalyzer.analyze

    def analyze(self, state):
        existing = tuple(original_analyze(self, state))
        existing_ids = {engine.engine_id for engine in existing}
        additions = tuple(
            engine
            for engine in _bond_scaler_engines(state)
            if engine.engine_id not in existing_ids
        )
        return (*existing, *additions)

    RealizedEngineAnalyzer.analyze = analyze
    RealizedEngineAnalyzer._bond_scaler_health_installed = True
