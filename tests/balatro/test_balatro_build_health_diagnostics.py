from types import SimpleNamespace

import games.balatro.build_health_diagnostics as diagnostics
from games.balatro.bonds.model import BondRank
from games.balatro.build_health import BuildHealth


def _health():
    return BuildHealth(
        total=50.0,
        survival=60.0,
        immediate=60.0,
        scaling=40.0,
        coherence=50.0,
        runway=50.0,
        critical=False,
        scaling_deficit=True,
        warnings=("fixture",),
        engines=(),
    )


def test_diagnostics_are_tracker_free_and_serialize_bond_component_fields(monkeypatch):
    class _Health:
        def evaluate(self, state):
            del state
            return _health()

    class _Roles:
        def classify(self, state):
            del state
            return (
                SimpleNamespace(
                    index=0,
                    name="The Tribe",
                    role=SimpleNamespace(value="CORE"),
                    bond_id="flush",
                    bond_rank=BondRank.R4,
                    realized_engine_id=None,
                    rationale=("fixture",),
                ),
            )

    monkeypatch.setattr(diagnostics, "_HEALTH", _Health())
    monkeypatch.setattr(diagnostics, "_ROLES", _Roles())

    payload = diagnostics.build_health_diagnostics_payload(SimpleNamespace())

    assert payload["total"] == 50.0
    assert payload["scaling_deficit"] is True
    assert payload["components"][0]["bond_id"] == "flush"
    assert payload["components"][0]["bond_rank"] == "R4"
    assert "strategy_id" not in payload["components"][0]
    assert "tier" not in payload["components"][0]
