from __future__ import annotations

import json

from games.balatro.tuning.shop_stall_diagnostics import (
    LiveTuningShopTrace,
    install_live_tuning_shop_diagnostics,
)


class _Target:
    label = "Arcana Pack"


class _Action:
    target = _Target()


class _Profiler:
    def profile(self, *args, **kwargs):
        del args, kwargs
        return "profile"


class _Expectation:
    def evaluate(self, *args, **kwargs):
        del args, kwargs
        return "expectation"


class _Policy:
    def __init__(self):
        self.build_profiler = _Profiler()
        self._arcana_generator_expectation = _Expectation()

    @staticmethod
    def _family(target):
        del target
        return "ARCANA"

    @staticmethod
    def _variant(target):
        del target
        return "NORMAL"

    def recommend(self, *args, **kwargs):
        del args, kwargs
        return "recommendation"


class _Utility:
    def baseline_gain(self, *args, **kwargs):
        del args, kwargs
        return "baseline"

    def joker_gain(self, *args, **kwargs):
        del args, kwargs
        return "joker"

    def consumable_gain(self, *args, **kwargs):
        del args, kwargs
        return "consumable"

    def booster_gain(self, *args, **kwargs):
        del args, kwargs
        return "booster"


class _ShopPolicy:
    def rank_actions(self, *args, **kwargs):
        del args, kwargs
        return []


class _Generator:
    def generate_actions(self, *args, **kwargs):
        del args, kwargs
        return []


class _Arbiter:
    def __init__(self):
        self.shop_policy = _ShopPolicy()
        self.utility_scale = _Utility()
        self.booster = _Policy()
        self.reroll = _Policy()

    def _pending_bond_pair_completion(self, *args, **kwargs):
        del args, kwargs
        return None

    def _rank_deterministic_actions(self, *args, **kwargs):
        del args, kwargs
        return []

    def _best_joker_decision(self, *args, **kwargs):
        del args, kwargs
        return None

    def _standalone_joker_decisions(self, *args, **kwargs):
        del args, kwargs
        return ()

    def _best_consumable_decision(self, *args, **kwargs):
        del args, kwargs
        return None

    def _booster_policy_for_state(self, *args, **kwargs):
        del args, kwargs
        return self.booster

    def _reroll_policy_for_state(self, *args, **kwargs):
        del args, kwargs
        return self.reroll

    def _best_visible_bond_pair(self, *args, **kwargs):
        del args, kwargs
        return None

    def decide(self, *args, **kwargs):
        del args, kwargs
        return "decision"


class _Runner:
    def __init__(self):
        self.shop_generator = _Generator()
        self.shop_arbiter = _Arbiter()
        self.reroll_terms_reader = lambda: "terms"

    def _recommend_consumable_use(self, *args, **kwargs):
        del args, kwargs
        return None


class _Supervisor:
    def __init__(self):
        self.runner_factory = lambda observer: _Runner()


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_trace_records_begin_end_without_changing_return_value(tmp_path):
    path = tmp_path / "trace.jsonl"
    trace = LiveTuningShopTrace(path)

    assert trace.timed("EXAMPLE", lambda: 42, trace_details={"family": "ARCANA"}) == 42

    events = _events(path)
    assert [(event["stage"], event["status"]) for event in events] == [
        ("EXAMPLE", "BEGIN"),
        ("EXAMPLE", "END"),
    ]
    assert events[0]["family"] == "ARCANA"
    assert events[-1]["elapsed_seconds"] >= 0.0


def test_supervisor_factory_installs_durable_shop_stage_wrappers(tmp_path):
    path = tmp_path / "trace.jsonl"
    supervisor = _Supervisor()

    assert install_live_tuning_shop_diagnostics(supervisor, trace_path=path) is True
    runner = supervisor.runner_factory(object())

    assert runner._recommend_consumable_use(object()) is None
    assert runner.shop_generator.generate_actions(object()) == []
    assert runner.reroll_terms_reader() == "terms"
    assert runner.shop_arbiter._standalone_joker_decisions(object()) == ()
    assert runner.shop_arbiter._rank_deterministic_actions(object()) == []
    assert runner.shop_arbiter._best_joker_decision(object()) is None
    assert runner.shop_arbiter._best_consumable_decision(object()) is None
    assert runner.shop_arbiter._best_visible_bond_pair(object()) is None
    booster = runner.shop_arbiter._booster_policy_for_state(object())
    assert booster.build_profiler.profile(object()) == "profile"
    assert booster._arcana_generator_expectation.evaluate(object()) == "expectation"
    assert booster.recommend(object(), _Action()) == "recommendation"
    assert runner.shop_arbiter._reroll_policy_for_state(object()).recommend(object()) == "recommendation"
    assert runner.shop_arbiter.decide(object()) == "decision"

    events = _events(path)
    stages = {event["stage"] for event in events}
    assert "RUNNER_INSTRUMENTATION" in stages
    assert "SHOP_PRE_D14_CONSUMABLE_CHECK" in stages
    assert "SHOP_ACTION_GENERATION" in stages
    assert "SHOP_REROLL_TERMS_READ" in stages
    assert "D14_JOKER_STANDALONE" in stages
    assert "D14_JOKER" in stages
    assert "D14_CONSUMABLE" in stages
    assert "D14_VISIBLE_BOND_PAIR" in stages
    assert "D8_BUILD_PROFILE" in stages
    assert "D8_ARCANA_EXPECTATION" in stages
    assert "D14_BOOSTER_RECOMMEND" in stages
    assert "D14_REROLL_RECOMMEND" in stages
    assert "D14_TOTAL" in stages

    booster_events = [
        event for event in events if event["stage"] == "D14_BOOSTER_RECOMMEND"
    ]
    assert booster_events
    assert booster_events[0]["booster_family"] == "ARCANA"
    assert booster_events[0]["booster_variant"] == "NORMAL"
    assert booster_events[0]["booster_label"] == "Arcana Pack"
