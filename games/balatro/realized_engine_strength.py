from __future__ import annotations

from dataclasses import dataclass

from games.balatro.build_health import EngineState, RealizedEngineStrength


def _name(value) -> str:
    return "".join(ch for ch in str(getattr(value, "name", value) or "").lower() if ch.isalnum())


def _owned(state, *names: str):
    wanted = {_name(name) for name in names}
    return [joker for joker in getattr(state, "jokers", ()) if _name(joker) in wanted]


def _first(state, *names: str):
    values = _owned(state, *names)
    return values[0] if values else None


def _state_from_progress(progress: float, *, active: bool = True) -> EngineState:
    if not active:
        return EngineState.OWNED_INACTIVE
    if progress >= 1.0:
        return EngineState.MATURE
    if progress >= 0.60:
        return EngineState.ACTIVATED_HEALTHY
    return EngineState.ACTIVATED_WEAK


@dataclass(frozen=True)
class RealizedEngineObserver:
    """Translate public run state into realized engine descriptors.

    This layer deliberately reports mechanics, not strategy desirability. Thresholds
    are normalized against the current blind where possible so engine maturity is
    not confused with catalogue tier or hypothetical ceiling.
    """

    def observe(self, state) -> tuple[RealizedEngineStrength, ...]:
        engines: list[RealizedEngineStrength] = []
        engines.extend(self._deck_growth(state))
        engines.extend(self._mutable_scalers(state))
        cash = self._cash_engine(state)
        if cash is not None:
            engines.append(cash)
        return tuple(engines)

    @staticmethod
    def _blind(state) -> float:
        return max(1.0, float(getattr(state, "blind_requirement", 0) or 1.0))

    def _deck_growth(self, state) -> list[RealizedEngineStrength]:
        result: list[RealizedEngineStrength] = []
        hologram = _first(state, "Hologram", "Hologram Joker")
        blue = _first(state, "Blue Joker")
        generators = _owned(state, "Certificate", "Marble Joker", "DNA")
        owned_deck = getattr(state, "owned_deck", None)
        deck_size = len(owned_deck) if owned_deck is not None else len(getattr(state, "deck", ()))
        growth_cards = max(0, deck_size - 52)

        if hologram is not None:
            x_mult = max(1.0, float(getattr(hologram, "x_mult", 1.0) or 1.0))
            active = x_mult > 1.0 + 1e-9
            progress = min(1.0, max(0.0, (x_mult - 1.0) / 1.5))
            result.append(
                RealizedEngineStrength(
                    engine_id="hologram_deck_growth",
                    state=_state_from_progress(progress, active=active),
                    current_strength=x_mult,
                    growth_rate=0.15 * len(generators),
                    runway_need=max(0.0, 1.0 - progress),
                    rationale=(
                        f"x_mult={x_mult:.3f}",
                        f"card_generators={len(generators)}",
                        f"cards_above_base={growth_cards}",
                    ),
                )
            )

        if blue is not None:
            # Blue Joker is immediately functional; deck growth increases its
            # ceiling but it is not an inactive engine merely because no generator
            # has been found yet.
            progress = min(1.0, max(0.0, deck_size / 80.0))
            result.append(
                RealizedEngineStrength(
                    engine_id="blue_joker_deck_size",
                    state=_state_from_progress(progress),
                    current_strength=float(deck_size),
                    growth_rate=float(len(generators)),
                    runway_need=max(0.0, 1.0 - progress),
                    rationale=(
                        f"owned_deck_size={deck_size}",
                        f"card_generators={len(generators)}",
                    ),
                )
            )
        return result

    def _mutable_scalers(self, state) -> list[RealizedEngineStrength]:
        result: list[RealizedEngineStrength] = []
        blind = self._blind(state)
        specs = (
            ("Green Joker", "green_joker", "mult", 4.0),
            ("Castle", "castle", "chips", 25.0),
            ("Runner", "runner", "chips", 25.0),
            ("Red Card", "red_card", "mult", 3.0),
        )
        for joker_name, engine_id, field, baseline in specs:
            joker = _first(state, joker_name)
            if joker is None:
                continue
            value = max(0.0, float(getattr(joker, field, 0.0) or 0.0))
            # Normalize additive engine progress against blind scale. The square
            # root prevents large blind numbers from making every additive scaler
            # appear permanently inactive while still tightening expectations as
            # Antes rise.
            target = max(baseline, blind ** 0.5)
            progress = min(1.0, value / target)
            result.append(
                RealizedEngineStrength(
                    engine_id=engine_id,
                    state=_state_from_progress(progress, active=value > 0.0),
                    current_strength=value,
                    growth_rate=0.0,
                    runway_need=max(0.0, 1.0 - progress),
                    rationale=(f"{field}={value:.3f}", f"blind_scaled_target={target:.3f}"),
                )
            )
        return result

    def _cash_engine(self, state) -> RealizedEngineStrength | None:
        bull = _first(state, "Bull")
        bootstraps = _first(state, "Bootstraps")
        if bull is None and bootstraps is None:
            return None
        money = max(0, int(getattr(state, "money", 0) or 0))
        chips = money * 2 if bull is not None else 0
        mult = (money // 5) * 2 if bootstraps is not None else 0
        # Cash engines are immediately realized. Pairing both increases coherence;
        # maturity is derived from their current output rather than a fixed dollar
        # threshold, matching the approved pivot rule.
        blind = self._blind(state)
        rough_output = float(chips) * max(1.0, float(mult))
        progress = min(1.0, rough_output / max(1.0, blind * 0.35))
        return RealizedEngineStrength(
            engine_id="bull_bootstraps_cash",
            state=_state_from_progress(progress, active=money > 0),
            current_strength=rough_output,
            growth_rate=float(money),
            runway_need=max(0.0, 1.0 - progress),
            rationale=(
                f"money={money}",
                f"bull_chips={chips}",
                f"bootstraps_mult={mult}",
                f"pair_owned={bull is not None and bootstraps is not None}",
            ),
        )
