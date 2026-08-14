from types import SimpleNamespace

from games.balatro.live.external.balatro_agent_supervisor import (
    BalatroAgentSupervisor,
    DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS,
)
from games.balatro.live.external.live_memory_supervisor_observer import (
    SupervisorLiveMemoryBalatroObserver,
    native_blind_select_ready,
    native_shop_ready,
)


class _Decoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return dict(self.tables.get(address, {}))


def _value(kind, value):
    return SimpleNamespace(kind=kind, value=value)


def test_native_blind_select_readiness_requires_real_on_deck_and_pane():
    decoder = _Decoder(
        {
            1: {},
            2: {},
        }
    )
    root = {
        "GAME": _value("table", 1),
        "blind_select_opts": _value("table", 2),
    }
    assert native_blind_select_ready(decoder, root) is False

    decoder.tables[1] = {"blind_on_deck": _value("string", "Small")}
    assert native_blind_select_ready(decoder, root) is False

    decoder.tables[2] = {"small": _value("table", 3)}
    assert native_blind_select_ready(decoder, root) is True


def test_native_shop_readiness_requires_real_card_areas_not_offer_counts():
    # Area tables: 10/20/30. Each has a real cards table and positive configured
    # capacity; the cards tables themselves are intentionally empty to prove that
    # purchases reducing visible offer count to zero do not make the shop unready.
    decoder = _Decoder(
        {
            10: {"cards": _value("table", 11), "config": _value("table", 12)},
            11: {},
            12: {"card_limit": _value("number", 2)},
            20: {"cards": _value("table", 21), "config": _value("table", 22)},
            21: {},
            22: {"card_limit": _value("number", 1)},
            30: {"cards": _value("table", 31), "config": _value("table", 32)},
            31: {},
            32: {"card_limit": _value("number", 2)},
        }
    )
    root = {}
    assert native_shop_ready(decoder, root) is False

    root["shop_jokers"] = _value("table", 10)
    assert native_shop_ready(decoder, root) is False

    root["shop_vouchers"] = _value("table", 20)
    assert native_shop_ready(decoder, root) is False

    root["shop_booster"] = _value("table", 30)
    assert native_shop_ready(decoder, root) is True

    # A zero/absent configured capacity is the signature of the premature SHOP
    # snapshot that previously normalized to count=0, limit=0 and triggered an
    # early END_SHOP.
    decoder.tables[12] = {"card_limit": _value("number", 0)}
    assert native_shop_ready(decoder, root) is False


def test_supervisor_defaults_to_readiness_aware_observer_and_longer_bridge_timeout(tmp_path):
    supervisor = BalatroAgentSupervisor(
        session_directory=tmp_path / "sessions",
        run_log_directory=tmp_path / "runs",
    )

    assert supervisor.observer_factory is SupervisorLiveMemoryBalatroObserver

    runner = supervisor.runner_factory(SimpleNamespace())
    assert runner.bridge.timeout == DEFAULT_SUPERVISOR_BRIDGE_TIMEOUT_SECONDS
    assert runner.bridge.timeout == 10.0
