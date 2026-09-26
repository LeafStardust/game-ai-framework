"""Fixed-state cost attribution for the production PPO tactical authority."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from time import perf_counter
from typing import Callable

from games.balatro.env.blind_progression import activate_selected_blind_progression
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.ppo_campaign import make_ppo_training_environment
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_learner import PPOLearner
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode
from games.balatro.env.parity import canonical_public_state_signature
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.select_blind import select_blind_exact


PPO_TACTICAL_COST_SCHEMA = "balatro-red-white-ppo-tactical-cost-v1"
PPO_TACTICAL_COST_WORKLOAD = "red-white-ppo-first-episode-first-small-blind-decision-v1"
PPO_TACTICAL_EPISODE_COST_SCHEMA = "balatro-red-white-ppo-tactical-episode-cost-v1"


@dataclass(frozen=True)
class PPOTacticalCostReport:
    schema: str
    workload: str
    root_seed: str
    game_seed: str
    action: str
    selected_hand_indices: tuple[int, ...]
    search_attempts: tuple[tuple[int, int, int, bool], ...]
    total_elapsed_seconds: float
    candidate_generation_elapsed_seconds: float
    search_evaluation_elapsed_seconds: float
    policy_arbitration_elapsed_seconds: float
    other_elapsed_seconds: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True)
class PPOTacticalEpisodeDecisionCost:
    public_input_sha256: str
    action: str
    selected_hand_indices: tuple[int, ...]
    search_attempts: tuple[tuple[int, int, int, bool], ...]
    total_elapsed_seconds: float
    candidate_generation_elapsed_seconds: float
    search_evaluation_elapsed_seconds: float
    policy_arbitration_elapsed_seconds: float
    other_elapsed_seconds: float


@dataclass(frozen=True)
class PPOTacticalEpisodeCostReport:
    schema: str
    root_seed: str
    episode_index: int
    stream_index: int
    game_seed: str
    environment_transitions: int
    total_elapsed_seconds: float
    tactical_elapsed_seconds: float
    decisions: tuple[PPOTacticalEpisodeDecisionCost, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass
class _CostAccumulator:
    candidate_generation: float = 0.0
    ranked_search: float = 0.0
    policy_arbitration: float = 0.0


def _timed_call(clock, accumulator: _CostAccumulator, field: str, function):
    def timed(*args, **kwargs):
        started = float(clock())
        try:
            return function(*args, **kwargs)
        finally:
            setattr(
                accumulator,
                field,
                getattr(accumulator, field) + float(clock()) - started,
            )

    return timed


def _instrument_planner(planner, clock, accumulator: _CostAccumulator) -> None:
    planner._candidate_actions = _timed_call(
        clock,
        accumulator,
        "candidate_generation",
        planner._candidate_actions,
    )


def _public_input_sha256(state) -> str:
    signature = canonical_public_state_signature(state)
    content = json.dumps(signature, separators=(",", ":"), ensure_ascii=True)
    return sha256(content.encode("ascii")).hexdigest()


def _instrument_episode_engine(engine, clock, records) -> None:
    active = {"cost": None}

    def timed(field, function):
        def wrapped(*args, **kwargs):
            accumulator = active["cost"]
            if accumulator is None:
                return function(*args, **kwargs)
            started = float(clock())
            try:
                return function(*args, **kwargs)
            finally:
                setattr(
                    accumulator,
                    field,
                    getattr(accumulator, field) + float(clock()) - started,
                )

        return wrapped

    def instrument_planner(planner):
        planner._candidate_actions = timed(
            "candidate_generation",
            planner._candidate_actions,
        )

    instrument_planner(engine.planner)
    original_adaptive_planner = engine._adaptive_planner

    def adaptive_planner(config):
        planner = original_adaptive_planner(config)
        instrument_planner(planner)
        return planner

    engine._adaptive_planner = adaptive_planner
    engine.rank_plans = timed("ranked_search", engine.rank_plans)
    engine.policy.decide = timed("policy_arbitration", engine.policy.decide)
    original_decide = engine.decide

    def decide(state):
        accumulator = _CostAccumulator()
        active["cost"] = accumulator
        started = float(clock())
        try:
            decision = original_decide(state)
        finally:
            total = float(clock()) - started
            active["cost"] = None

        search_evaluation = max(
            0.0,
            accumulator.ranked_search - accumulator.candidate_generation,
        )
        policy = accumulator.policy_arbitration
        other = max(0.0, total - accumulator.ranked_search - policy)
        records.append(
            PPOTacticalEpisodeDecisionCost(
                public_input_sha256=_public_input_sha256(state),
                action=decision.action.name,
                selected_hand_indices=tuple(
                    state.hand.index(card) for card in decision.action.cards
                ),
                search_attempts=tuple(
                    (
                        attempt.horizon,
                        attempt.nodes_evaluated,
                        attempt.max_nodes,
                        attempt.budget_exceeded,
                    )
                    for attempt in decision.search_attempts
                ),
                total_elapsed_seconds=total,
                candidate_generation_elapsed_seconds=accumulator.candidate_generation,
                search_evaluation_elapsed_seconds=search_evaluation,
                policy_arbitration_elapsed_seconds=policy,
                other_elapsed_seconds=other,
            )
        )
        return decision

    engine.decide = decide


def trace_first_ppo_episode_tactical_costs(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> tuple[PPOTacticalEpisodeDecisionCost, ...]:
    """Run episode zero and return ordered per-decision tactical cost evidence."""
    return trace_initial_policy_ppo_episode_tactical_costs(
        episode_index=0,
        root_seed=root_seed,
        clock=clock,
    ).decisions


def trace_initial_policy_ppo_episode_tactical_costs(
    *,
    episode_index: int,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalEpisodeCostReport:
    """Trace one exact pre-optimizer episode without replaying earlier streams."""
    if not isinstance(root_seed, str) or not root_seed:
        raise ValueError("root_seed must be a nonempty string")
    if not callable(clock):
        raise TypeError("clock must be callable")
    stream_count = PPO_TRAINING_CONTRACT.parallel_environments
    if (
        isinstance(episode_index, bool)
        or not isinstance(episode_index, int)
        or not 0 <= episode_index < stream_count
    ):
        raise PPOContractError(
            "PPO tactical episode diagnostic requires a first-wave episode index"
        )

    training_run = PPOTrainingRun.from_seed(root_seed)
    environment = make_ppo_training_environment(episode_index)
    learner = PPOLearner(training_run)
    records: list[PPOTacticalEpisodeDecisionCost] = []
    _instrument_episode_engine(
        environment._backend._tactical_decision_engine,
        clock,
        records,
    )

    started = float(clock())
    episode = collect_complete_ppo_episode(
        environment,
        training_run,
        episode_index=episode_index,
        policy=learner.model.infer,
    )
    total = float(clock()) - started
    if episode.episode_index != episode_index:
        raise RuntimeError("PPO tactical episode diagnostic episode index drifted")
    tactical = sum(record.total_elapsed_seconds for record in records)
    if any(not math.isfinite(value) or value < 0.0 for value in (total, tactical)):
        raise RuntimeError("PPO tactical episode diagnostic produced invalid timing")
    return PPOTacticalEpisodeCostReport(
        schema=PPO_TACTICAL_EPISODE_COST_SCHEMA,
        root_seed=root_seed,
        episode_index=episode_index,
        stream_index=episode_index,
        game_seed=training_run.game_seed(episode_index),
        environment_transitions=len(episode.decisions),
        total_elapsed_seconds=total,
        tactical_elapsed_seconds=tactical,
        decisions=tuple(records),
    )


def measure_ppo_tactical_cost(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalCostReport:
    """Measure one exact production decision without changing its search contract."""
    if not isinstance(root_seed, str) or not root_seed:
        raise ValueError("root_seed must be a nonempty string")
    if not callable(clock):
        raise TypeError("clock must be callable")

    training_run = PPOTrainingRun.from_seed(root_seed)
    game_seed = training_run.game_seed(0)
    run = pristine_red_white_reset(game_seed)
    run = activate_selected_blind_progression(run)
    run = select_blind_exact(run)
    state = public_observation_state(run.public)

    environment = make_ppo_training_environment(0)
    engine = environment._backend._tactical_decision_engine
    accumulator = _CostAccumulator()
    _instrument_planner(engine.planner, clock, accumulator)

    original_adaptive_planner = engine._adaptive_planner

    def instrumented_adaptive_planner(config):
        planner = original_adaptive_planner(config)
        _instrument_planner(planner, clock, accumulator)
        return planner

    engine._adaptive_planner = instrumented_adaptive_planner
    engine.rank_plans = _timed_call(
        clock,
        accumulator,
        "ranked_search",
        engine.rank_plans,
    )
    engine.policy.decide = _timed_call(
        clock,
        accumulator,
        "policy_arbitration",
        engine.policy.decide,
    )

    started = float(clock())
    decision = engine.decide(state)
    total = float(clock()) - started
    search_evaluation = max(
        0.0,
        accumulator.ranked_search - accumulator.candidate_generation,
    )
    other = max(
        0.0,
        total - accumulator.ranked_search - accumulator.policy_arbitration,
    )
    timings = (
        total,
        accumulator.candidate_generation,
        search_evaluation,
        accumulator.policy_arbitration,
        other,
    )
    if any(not math.isfinite(value) or value < 0.0 for value in timings):
        raise RuntimeError("PPO tactical diagnostic produced invalid timing")

    return PPOTacticalCostReport(
        schema=PPO_TACTICAL_COST_SCHEMA,
        workload=PPO_TACTICAL_COST_WORKLOAD,
        root_seed=root_seed,
        game_seed=game_seed,
        action=decision.action.name,
        selected_hand_indices=tuple(
            state.hand.index(card) for card in decision.action.cards
        ),
        search_attempts=tuple(
            (
                attempt.horizon,
                attempt.nodes_evaluated,
                attempt.max_nodes,
                attempt.budget_exceeded,
            )
            for attempt in decision.search_attempts
        ),
        total_elapsed_seconds=total,
        candidate_generation_elapsed_seconds=accumulator.candidate_generation,
        search_evaluation_elapsed_seconds=search_evaluation,
        policy_arbitration_elapsed_seconds=accumulator.policy_arbitration,
        other_elapsed_seconds=other,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-seed", default="RED-WHITE-PPO-V1")
    parser.add_argument("--episode-index", type=int)
    arguments = parser.parse_args(argv)
    report = (
        measure_ppo_tactical_cost(root_seed=arguments.root_seed)
        if arguments.episode_index is None
        else trace_initial_policy_ppo_episode_tactical_costs(
            episode_index=arguments.episode_index,
            root_seed=arguments.root_seed,
        )
    )
    print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
