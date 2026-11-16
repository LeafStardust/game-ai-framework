from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_SCHEMA,
    PUBLIC_ACTION_VERSION,
    action_index,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.episode_backend import (
    PPOHeadlessBackend,
    pristine_red_white_reset,
)
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_VERSION
from games.balatro.env.ppo_campaign import make_ppo_tactical_decision_engine
from games.balatro.env.ppo_candidate_evaluation import fixed_candidate_policy_seed
from games.balatro.env.ppo_strategic_shop_trace import (
    PPOStrategicShopTraceError,
    _TracingPPOHeadlessBackend,
    _load_reproduction,
    _shop_dict,
    make_strategic_trace_environment,
    run_strategic_shop_trace,
    summarize_strategic_shop_trace,
)
from games.balatro.env.seeded_evaluation import FIXED_SEEDED_EPISODES
from games.balatro.env.shop_booster_generation import GeneratedShopBoosterItem
from games.balatro.env.shop_consumable_items import GeneratedShopConsumableItem
from games.balatro.env.shop_items import GeneratedShopJokerItem
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.live.hand_action_policy import SEARCH_SCHEDULE_SELECTIVE


def _action(alias, params=None):
    return EnvAction.from_alias(alias, params)


class _OneCardTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(
            action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
        )


def _decision(index, action, *, money_before, money_after, affordable=()):
    selected_index = action_index(action)
    mask = [False] * len(PUBLIC_ACTION_SCHEMA.slots)
    probabilities = [0.0] * len(mask)
    mask[selected_index] = True
    probabilities[selected_index] = 1.0
    return {
        "decision_index": index,
        "before": {
            "frame": {"phase": "SHOP", "money": money_before},
            "shop": {
                "affordable_purchase_actions": [
                    {"alias": value.alias, "params": dict(value.params)}
                    for value in affordable
                ]
            },
        },
        "observation_schema_version": PUBLIC_OBSERVATION_VERSION,
        "observation_sha256": "0" * 64,
        "action_mask_schema_version": PUBLIC_ACTION_VERSION,
        "action_mask": mask,
        "probabilities": probabilities,
        "value_estimate": -0.25,
        "selected_action_index": selected_index,
        "selected_action": {
            "alias": action.alias,
            "params": dict(action.params),
        },
        "after": {"money": money_after},
    }


def _episodes():
    episodes = []
    for spec in FIXED_SEEDED_EPISODES:
        decisions = []
        if spec.episode_index == 0:
            voucher = _action("BUY_VOUCHER", {"slot": 0})
            joker = _action("BUY_JOKER", {"slot": 0})
            decisions = [
                _decision(
                    0,
                    voucher,
                    money_before=12,
                    money_after=2,
                    affordable=(voucher,),
                ),
                _decision(
                    1,
                    _action("END_SHOP"),
                    money_before=5,
                    money_after=5,
                    affordable=(joker,),
                ),
            ]
        episodes.append(
            {
                "episode_index": spec.episode_index,
                "game_seed": spec.game_seed,
                "policy_seed": fixed_candidate_policy_seed(spec),
                "metrics": {
                    "ante_reached": 2 if spec.episode_index == 0 else 1,
                    "terminal_requirement_progress": (
                        0.75 if spec.episode_index == 0 else 0.5
                    ),
                },
                "decisions": decisions,
            }
        )
    return tuple(episodes)


def test_trace_uses_the_unchanged_selective_production_factory():
    recorders = []

    make_strategic_trace_environment(recorders)

    assert len(recorders) == 1
    assert isinstance(recorders[0], _TracingPPOHeadlessBackend)
    assert (
        recorders[0]._tactical_decision_engine.search_schedule_mode
        == SEARCH_SCHEDULE_SELECTIVE
    )
    assert type(recorders[0]._tactical_decision_engine) is type(
        make_ppo_tactical_decision_engine()
    )


def test_tracing_backend_observes_without_changing_a_strategic_transition():
    production = PPOHeadlessBackend(_OneCardTacticalPolicy())
    tracing = _TracingPPOHeadlessBackend(_OneCardTacticalPolicy())
    production.reset("TRACE-SKIP")
    tracing.reset("TRACE-SKIP")
    production.run.public.hand_levels["HIGH_CARD"] = 1000
    tracing.run.public.hand_levels["HIGH_CARD"] = 1000
    action = _action("SELECT_BLIND")
    assert action in production.legal_actions()

    expected = production.step(action)
    actual = tracing.step(action)

    assert actual.reward == expected.reward
    assert actual.truncated is expected.truncated is False
    assert actual.frame.status is expected.frame.status
    assert actual.frame.owner is expected.frame.owner
    assert actual.frame.info == expected.frame.info
    assert tracing.serialize() == production.serialize()
    assert len(tracing.transitions) == 1
    assert tracing.transitions[0]["selected_action"]["alias"] == "SELECT_BLIND"


def test_shop_snapshot_uses_canonical_item_metadata_and_exact_legality():
    run = pristine_red_white_reset("TRACE-SHOP")
    state = run.public
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 12
    run.reroll_cost = 7
    state.shop_jokers = [
        GeneratedShopJokerItem("j_joker", 1, 2, None, 2, False)
    ]
    state.shop_consumables = [
        GeneratedShopConsumableItem("Tarot", "c_fool", 3, 3, False)
    ]
    state.shop_boosters = [
        GeneratedShopBoosterItem(
            "p_buffoon_normal_1", "Buffoon", "Buffoon Pack", 4, 4, 2, 1, 1, False
        )
    ]
    state.shop_vouchers = [
        GeneratedShopVoucherItem("v_grabber", 10, 10, 0, False)
    ]
    legal = (
        _action("BUY_JOKER", {"slot": 0}),
        _action("REROLL_SHOP"),
        _action("END_SHOP"),
        _action("SELL_JOKER", {"joker_index": 0}),
    )

    snapshot = _shop_dict(run, legal)

    assert snapshot["reroll_cost"] == 7
    assert snapshot["reroll_cost_policy_observed"] is False
    assert snapshot["visible"]["jokers"][0]["fields"]["center_key"] == "j_joker"
    assert snapshot["visible"]["consumables"][0]["fields"]["price"] == 3
    assert snapshot["visible"]["boosters"][0]["fields"]["pack_size"] == 2
    assert snapshot["visible"]["vouchers"][0]["fields"]["price"] == 10
    assert [
        value["alias"]
        for value in snapshot["legal_purchase_end_reroll_actions"]
    ] == ["BUY_JOKER", "REROLL_SHOP", "END_SHOP"]
    assert [
        value["alias"] for value in snapshot["affordable_purchase_actions"]
    ] == ["BUY_JOKER"]


def test_summary_publishes_shop_sequences_acquisitions_and_terminal_outcomes():
    summary = summarize_strategic_shop_trace(_episodes())

    assert summary["episode_count"] == 64
    assert summary["episodes_with_shop"] == 1
    assert summary["strategic_decision_count"] == 2
    assert summary["shop_decision_count"] == 2
    assert summary["end_shop_with_affordable_purchase_count"] == 1
    assert summary["purchase_count"] == 1
    assert summary["mean_purchase_money_delta"] == -10
    assert {
        value["alias"]: value["count"]
        for value in summary["acquisition_family_frequencies"]
    }["BUY_VOUCHER"] == 1
    episode = summary["episode_shop_sequences"][0]
    assert episode["terminal_ante"] == 2
    assert episode["terminal_requirement_progress"] == 0.75
    assert [value["money_after"] for value in episode["decisions"]] == [2, 5]


def test_summary_rejects_reordered_episodes_and_invalid_probability_evidence():
    with pytest.raises(PPOStrategicShopTraceError, match="out of order"):
        summarize_strategic_shop_trace(tuple(reversed(_episodes())))

    malformed = list(deepcopy(_episodes()))
    malformed[0]["decisions"][0]["probabilities"][0] = 0.1
    with pytest.raises(
        PPOStrategicShopTraceError,
        match="mask/probabilities are invalid",
    ):
        summarize_strategic_shop_trace(tuple(malformed))


def test_trace_loads_exact_current_reproduction_and_rejects_reordered_source(
    tmp_path, monkeypatch
):
    source = Path(
        "docs/balatro/BALATRO_PPO_CURRENT_TACTICAL_REPRODUCTION.json"
    )
    report = _load_reproduction(source)
    assert len(report["episodes"]) == 64
    assert report["decision"] == "published-exact"

    reordered = deepcopy(report)
    reordered["episodes"].reverse()
    raw = json.dumps(
        reordered, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    path = tmp_path / "reordered.json"
    path.write_bytes(raw)
    monkeypatch.setattr(
        "games.balatro.env.ppo_strategic_shop_trace.CURRENT_REPRODUCTION_SHA256",
        sha256(raw).hexdigest(),
    )
    with pytest.raises(PPOStrategicShopTraceError, match="source order drifted"):
        _load_reproduction(path)


def test_trace_rejects_overwrite_before_loading_sources():
    with pytest.raises(PPOStrategicShopTraceError, match="already exists"):
        run_strategic_shop_trace(
            "missing-campaign",
            "missing-promotion",
            "missing-reproduction",
            __file__,
            maximum_workers=1,
        )
