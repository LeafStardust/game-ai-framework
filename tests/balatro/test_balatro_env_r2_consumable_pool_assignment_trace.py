import inspect
from pathlib import Path

import games.balatro.live.translator as translator_module
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.state import BalatroState


def test_env_r2_consumable_pool_has_no_post_owner_overwrite(monkeypatch):
    assignments = []

    class TrackingState(BalatroState):
        def __setattr__(self, name, value):
            if name in {
                "consumable_generation_pool_observed",
                "consumable_generation_pools",
            }:
                caller = inspect.currentframe().f_back
                assignments.append(
                    (
                        name,
                        tuple(value) if isinstance(value, dict) else value,
                        Path(caller.f_code.co_filename).name,
                        caller.f_code.co_name,
                        caller.f_lineno,
                    )
                )
            super().__setattr__(name, value)

    monkeypatch.setattr(translator_module, "BalatroState", TrackingState)
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SHOP",
        state_complete=True,
        payload={
            "consumable_generation_pool_observed": True,
            "consumable_generation_pools": {
                "Tarot": [
                    {
                        "type": "Tarot",
                        "key": "c_strength",
                        "cost": 3,
                        "unlocked": True,
                        "no_pool_flag": None,
                        "yes_pool_flag": None,
                        "softlock": False,
                        "hand_type": None,
                    }
                ],
                "Planet": [
                    {
                        "type": "Planet",
                        "key": "c_pluto",
                        "cost": 3,
                        "unlocked": True,
                        "no_pool_flag": None,
                        "yes_pool_flag": None,
                        "softlock": False,
                        "hand_type": None,
                    }
                ],
            },
        },
    )

    state = translator_module.DefaultBalatroStateTranslator().translate(snapshot)

    assert set(state.consumable_generation_pools) == {"Tarot", "Planet"}, assignments
