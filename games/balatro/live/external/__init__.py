"""Compatibility aliases for the pre-v0.9 ``live.external`` namespace.

The production implementation lives in :mod:`games.balatro.live.runtime`.  Legacy
imports still exist in tests and a few downstream callers, so this package exposes
the canonical runtime module objects under their former qualified names.  Using
module-object aliases (rather than loading the files twice) preserves class/function
identity and makes monkeypatching either namespace affect the same implementation.
"""

from importlib import import_module
import sys

_RUNTIME_MODULES = (
    "agent_control",
    "balatro_agent_crash_report",
    "balatro_agent_crash_report_repo",
    "balatro_agent_monitor",
    "balatro_agent_supervisor",
    "balatro_agent_supervisor_entry",
    "balatro_agent_toggle",
    "balatro_g_discovery",
    "finisher_state_translator",
    "live_memory_achievement_guard",
    "live_memory_autonomous_loop_injected",
    "live_memory_autonomous_stale_diagnostic",
    "live_memory_autonomous_step_injected",
    "live_memory_discard_history_observer",
    "live_memory_observer",
    "live_memory_pack_terms",
    "live_memory_restart_capability",
    "live_memory_restart_contract",
    "live_memory_restart_run_injected",
    "live_memory_shop_action_injected_validation",
    "live_memory_shop_terms",
    "live_memory_supervisor_observer",
    "luajit_memory",
    "luajit_non_gc64_memory",
    "playstyle_autonomous_runner",
    "process_locator",
    "process_memory",
    "save_observer",
    "save_state",
    "state_observer_factory",
    "v09g_diagnostic_report",
    "v09g_release_report",
)

for _name in _RUNTIME_MODULES:
    _module = import_module(f"games.balatro.live.runtime.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module

__all__ = list(_RUNTIME_MODULES)
