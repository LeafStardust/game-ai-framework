import pytest

from games.balatro.live.external import live_blind_runner
from games.balatro.live.external.live_memory_hand_executor import (
    LiveMemoryHandExecutionError,
)
from games.balatro.live.external.live_memory_observer import LiveMemoryBalatroObserver
from games.balatro.live.external.production_observer import ProductionBalatroObserver


def test_production_memory_observer_exposes_raw_live_observer():
    raw = LiveMemoryBalatroObserver(reader=object(), decoder=object(), g_table=1)
    production = ProductionBalatroObserver(raw)

    assert live_blind_runner._raw_memory_observer(production) is raw


def test_save_or_other_observer_cannot_arm_calibration_free_execution():
    with pytest.raises(LiveMemoryHandExecutionError, match="process-memory"):
        live_blind_runner._raw_memory_observer(object())


def test_runner_module_has_no_mouse_layout_dependency():
    assert not hasattr(live_blind_runner, "HandMouseLayout")
    assert not hasattr(live_blind_runner, "_load_execution_layout")
