from types import SimpleNamespace

from games.balatro.build_component_roles import (
    BuildComponentRole,
    BuildComponentRoleClassifier,
)
from games.balatro.build_health import EngineState, RealizedEngineStrength
from games.balatro.strategy import BANNED, GOLD, SILVER


def _joker(name):
    return SimpleNamespace(name=name)


class _Engines:
    def analyze(self, state):
        del state
        return (
            RealizedEngineStrength(
                engine_id="hologram",
                state=EngineState.OWNED_INACTIVE,
                current_strength=1.0,
            ),
        )


class _Tracker:
    def observe(self, state):
        del state
        return SimpleNamespace(dominant_strategy_id="flush")

    def primary_strategy_id(self, resolution):
        del resolution
        return "flush"

    def evaluate_item(self, state, joker, *, kind):
        del state, kind
        name = joker.name
        if name == "The Tribe":
            return SimpleNamespace(active_alignment=True, strategy_id="flush", tier=GOLD)
        if name == "Droll Joker":
            return SimpleNamespace(active_alignment=True, strategy_id="flush", tier=SILVER)
        if name == "Hologram":
            return SimpleNamespace(active_alignment=True, strategy_id="blue_joker_deck", tier=SILVER)
        if name == "Conflict":
            return SimpleNamespace(active_alignment=True, strategy_id="flush", tier=BANNED)
        return SimpleNamespace(active_alignment=False, strategy_id=None, tier=None)


def test_component_roles_distinguish_core_engine_support_filler_and_conflict():
    state = SimpleNamespace(
        jokers=[
            _joker("The Tribe"),
            _joker("Droll Joker"),
            _joker("Hologram"),
            _joker("Misprint"),
            _joker("Conflict"),
        ]
    )
    classifier = BuildComponentRoleClassifier(engine_analyzer=_Engines())

    roles = {
        item.name: item.role
        for item in classifier.classify(state, strategy_tracker=_Tracker())
    }

    assert roles["The Tribe"] == BuildComponentRole.CORE
    assert roles["Droll Joker"] == BuildComponentRole.SUPPORT
    assert roles["Hologram"] == BuildComponentRole.ENGINE
    assert roles["Misprint"] == BuildComponentRole.FILLER
    assert roles["Conflict"] == BuildComponentRole.CONFLICT
