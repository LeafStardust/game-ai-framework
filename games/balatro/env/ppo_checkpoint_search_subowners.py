"""Checkpoint-backed helper attribution for one tactical search evaluation."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Callable

from games.balatro.env.ppo_campaign import (
    PPO_CAMPAIGN_VERSION,
    _atomic_write,
    _canonical_bytes,
    _restore_session,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_campaign_wave_timing import _read_canonical_checkpoint
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode
from games.balatro.env.ppo_tactical_performance import (
    PPOTacticalCandidateSubownerReport,
    PPOTacticalEstimateDeepcopyCallsiteCost,
    _PPOTacticalScopedSubownerTrace,
    _trace_candidate_subowners,
)


PPO_CHECKPOINT_SEARCH_SUBOWNER_SCHEMA = (
    "balatro-red-white-ppo-checkpoint-search-subowner-v2"
)
EPISODE_INDEX = 637
TARGET_DECISION_INDEX = 11
EXPECTED_PREFIX = (
    ("4e76d753a3ee9ba814d2979295403cbd43371e5303c316867a99fd9d67331ff3", "DISCARD_CARDS", (0, 1, 2, 4, 7), ((2, 18, 2000, False),)),
    ("22e8cc32cbc871276797aebe81f58f8f6362e6faf3bceb124934ff1f1bd0ec34", "PLAY_CARDS", (1, 2, 5, 6), ((2, 18, 2000, False),)),
    ("9960a1b080786568fe35e0f75704800d3a6918b9cac1bab3f7774716794f054c", "DISCARD_CARDS", (0, 1, 2, 6, 7), ((2, 18, 2000, False),)),
    ("7213ceb4d30fef6a5e106fe8a5861e0f8487bc1a716d92a1a3c18462de6964ff", "PLAY_CARDS", (1, 2, 4, 5), ((2, 15, 2000, False),)),
    ("a649a6771c0885295717520af6e18c61dee02b49e99f508379b800114467480e", "PLAY_CARDS", (0, 1, 2, 3), ((2, 3, 2000, False),)),
    ("60392f79c4a0faec4c047705d56fa75871d2edc43c80a7c07f88010e78224da0", "DISCARD_CARDS", (0, 1, 5, 6, 7), ((2, 18, 2000, False),)),
    ("6ad826d10afbce21429e2326bbf41343f6557dba7a40a7f42be2850d5b5f0bb4", "DISCARD_CARDS", (0, 1, 2, 4, 5), ((2, 18, 2000, False),)),
    ("37e1312f3162589582c2781051282cfeec335da2119f0ef46812f79454667741", "PLAY_CARDS", (2, 3, 5, 6, 7), ((2, 18, 2000, False),)),
    ("17e5d95c571a5ee4ef44ed70ecc22d12c3c4e4433617f95925eda8a2a5e5fd97", "PLAY_CARDS", (0, 1, 2, 3), ((2, 15, 2000, False),)),
    ("cd57cd4950d10a141b65dbeb0b1a1b9edbbe02db695fcf76eb6e276d625e22ac", "PLAY_CARDS", (1, 2, 4, 5), ((2, 15, 2000, False),)),
    ("1a486f055dfdfc509258f2dd55ab38c94978739083f7a8e3e22a375f8c167d27", "PLAY_CARDS", (2, 3, 4, 5), ((2, 3, 2000, False),)),
    ("43da28597c26c6d105cb187b762f3cc81bf1fd13472228659fb9f2ed6a6465f4", "DISCARD_CARDS", (0, 1, 3, 4, 7), ((2, 292, 2000, False),)),
)
EPISODE_908_INDEX = 908
EPISODE_908_TARGET_DECISION_INDEX = 13
EPISODE_908_EXPECTED_PREFIX = (
    ("ac3252baf0337f77e9a7e546a69491c2240f5825abedcf8bfc9064b1f8aa956b", "DISCARD_CARDS", (0, 1, 3, 6, 7), ((2, 18, 2000, False),)),
    ("88615bc781b68ff376b43137d67aca540334c8bb99c9ec420ecc365ab585f127", "PLAY_CARDS", (0, 1, 2, 3), ((2, 18, 2000, False),)),
    ("c7d05bbbe2ad3802901343ca5fe0ab76a6815d5d2ee0702429590a36d236fb97", "DISCARD_CARDS", (0, 1), ((2, 18, 2000, False),)),
    ("bc0eaaafd172766156e7bf4191fa62d927dccc1493c1b1e4ead42c318d613d1f", "PLAY_CARDS", (1, 2, 4, 5), ((2, 18, 2000, False),)),
    ("d86935d598ce00bf1ce686c1bd8884a28919f840432b64b96e92e579a32f7d19", "PLAY_CARDS", (4, 5, 6, 7), ((2, 15, 2000, False),)),
    ("4cdfd7b6241e2cb1fc24fd553c410a78d2acf5cfe407747fee9a389f210953ae", "PLAY_CARDS", (2, 3, 6, 7), ((2, 3, 2000, False),)),
    ("b5ea3ba6698cb0e0bf200cd3fa05e9327f96fe10c4b6bce3c4c08e88b36a97c4", "PLAY_CARDS", (0, 1, 2), ((2, 18, 2000, False),)),
    ("d7e016717d4145f3d5777d0bae0e5f28b1fcfdf6c325236bc9929d5a08974592", "DISCARD_CARDS", (0, 1, 2, 3, 7), ((2, 18, 2000, False),)),
    ("e4dad2baeabcd57402136655526e407b568af751048b2b6fead0a3997d17a708", "PLAY_CARDS", (1, 2, 4, 5, 7), ((2, 15, 2000, False),)),
    ("6acf058dfbffe1af24d0f8a206621e14f22f53759b0002808750ee1f6e1994ec", "PLAY_CARDS", (0, 1, 3, 5, 7), ((2, 3, 2000, False),)),
    ("05074ebd3573c33a3a215c964624d67d3fa51067b9bb17ca624641cfbb12acb0", "PLAY_CARDS", (0, 1, 2, 3), ((2, 188, 2000, False),)),
    ("123c9be52a01f21ff11c6e9097b0ab2c315dc72c38f98b43ddd0a580155da835", "PLAY_CARDS", (1, 2, 3, 6, 7), ((2, 84, 2000, False), (2, 97, 1000, False))),
    ("2178483fcda49d503047569575c37a52e2ab644b2213a630ed3eb8462501446e", "DISCARD_CARDS", (1, 3, 4, 5, 6), ((2, 420, 2000, False),)),
    ("ab0790fbe59d21e18c52077a6894a4f7a4145d32901c94b39e35e1027bc346c7", "DISCARD_CARDS", (2, 3, 5), ((2, 420, 2000, False), (3, 1122, 2000, False), (3, 1000, 1000, True))),
)
PPO_CHECKPOINT_CANDIDATE_SUBOWNER_SCHEMA = (
    "balatro-red-white-ppo-checkpoint-candidate-subowner-v1"
)


@dataclass(frozen=True)
class PPOCheckpointSearchSubownerReport:
    schema: str
    campaign_version: str
    checkpoint_sha256: str
    training_run_sha256: str
    policy_parameter_sha256: str
    session_sha256_before: str
    session_sha256_after: str
    root_seed: str | int
    episode_index: int
    stream_index: int
    game_seed: str
    episode_sha256: str
    terminal_status: str
    environment_transitions: int
    committed: bool
    search_evaluation_elapsed_seconds: float
    policy_arbitration_elapsed_seconds: float
    other_elapsed_seconds: float
    residual_search_evaluation_elapsed_seconds: float
    estimate_state_deepcopy_calls: int
    estimate_state_deepcopy_elapsed_seconds: float
    estimate_state_deepcopy_callsites: tuple[
        PPOTacticalEstimateDeepcopyCallsiteCost, ...
    ]
    residual_estimate_state_deepcopy_elapsed_seconds: float
    target: PPOTacticalCandidateSubownerReport

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )


@dataclass(frozen=True)
class PPOCheckpointCandidateSubownerReport:
    schema: str
    campaign_version: str
    checkpoint_sha256: str
    training_run_sha256: str
    policy_parameter_sha256: str
    session_sha256_before: str
    session_sha256_after: str
    root_seed: str | int
    episode_index: int
    stream_index: int
    game_seed: str
    episode_sha256: str
    terminal_status: str
    environment_transitions: int
    committed: bool
    target: PPOTacticalCandidateSubownerReport

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )


def trace_checkpoint_candidate_subowners(
    root_seed: str | int,
    checkpoint_path: str | Path,
    *,
    clock: Callable[[], float] = perf_counter,
    environment_factory=make_ppo_training_environment,
    subowner_tracer=_trace_candidate_subowners,
    episode_collector=collect_complete_ppo_episode,
) -> PPOCheckpointCandidateSubownerReport:
    """Attribute episode-908 decision-13 candidate helpers, then replay terminal."""
    if not callable(clock):
        raise TypeError("clock must be callable")
    if not all(
        callable(value)
        for value in (environment_factory, subowner_tracer, episode_collector)
    ):
        raise TypeError("checkpoint candidate diagnostic dependencies must be callable")

    checkpoint_bytes, payload = _read_canonical_checkpoint(Path(checkpoint_path))
    training_run = PPOTrainingRun.from_seed(root_seed)
    session = _restore_session(training_run, payload, environment_factory)
    model = session.learner.model
    policy_sha256 = model.parameter_sha256
    stream_index = (
        EPISODE_908_INDEX % PPO_TRAINING_CONTRACT.parallel_environments
    )
    if (
        session.learner.assembler.next_episode_indices[stream_index]
        != EPISODE_908_INDEX
    ):
        raise PPOContractError(
            "checkpoint candidate target is not the pending stream index"
        )
    session_before = sha256(_canonical_bytes(session.serialize())).hexdigest()

    target = subowner_tracer(
        episode_index=EPISODE_908_INDEX,
        target_index=EPISODE_908_TARGET_DECISION_INDEX,
        expected_prefix=EPISODE_908_EXPECTED_PREFIX,
        root_seed=root_seed,
        clock=clock,
        environment=environment_factory(stream_index),
        policy=model.infer,
        helper_scope="candidate",
    )
    if not isinstance(target, PPOTacticalCandidateSubownerReport):
        raise PPOContractError("checkpoint candidate diagnostic returned invalid scope")
    if (
        target.verified_prefix_decisions != len(EPISODE_908_EXPECTED_PREFIX)
        or target.target_decision_index != EPISODE_908_TARGET_DECISION_INDEX
        or (
            target.public_input_sha256,
            target.action,
            target.selected_hand_indices,
            target.search_attempts,
        )
        != EPISODE_908_EXPECTED_PREFIX[-1]
    ):
        raise PPOContractError("checkpoint candidate target provenance drifted")

    episode = episode_collector(
        environment_factory(stream_index),
        training_run,
        episode_index=EPISODE_908_INDEX,
        policy=model.infer,
    )
    if model.parameter_sha256 != policy_sha256:
        raise PPOContractError("checkpoint candidate diagnostic policy changed")
    session_after = sha256(_canonical_bytes(session.serialize())).hexdigest()
    if session_after != session_before:
        raise PPOContractError("checkpoint candidate diagnostic mutated campaign state")
    if (
        episode.training_run != training_run
        or episode.episode_index != EPISODE_908_INDEX
        or episode.game_seed != training_run.game_seed(EPISODE_908_INDEX)
        or episode.truncated
        or not episode.status.terminal
    ):
        raise PPOContractError(
            "checkpoint candidate terminal episode provenance drifted"
        )

    timings = (
        target.total_elapsed_seconds,
        target.candidate_generation_elapsed_seconds,
        target.residual_candidate_elapsed_seconds,
        *(item.exclusive_elapsed_seconds for item in target.helper_costs),
    )
    if any(not math.isfinite(value) or value < 0.0 for value in timings):
        raise PPOContractError("checkpoint candidate diagnostic timing is invalid")
    if abs(
        target.candidate_generation_elapsed_seconds
        - sum(item.exclusive_elapsed_seconds for item in target.helper_costs)
        - target.residual_candidate_elapsed_seconds
    ) > 1e-9:
        raise PPOContractError("checkpoint candidate helper accounting drifted")

    return PPOCheckpointCandidateSubownerReport(
        schema=PPO_CHECKPOINT_CANDIDATE_SUBOWNER_SCHEMA,
        campaign_version=PPO_CAMPAIGN_VERSION,
        checkpoint_sha256=sha256(checkpoint_bytes).hexdigest(),
        training_run_sha256=training_run.sha256,
        policy_parameter_sha256=policy_sha256,
        session_sha256_before=session_before,
        session_sha256_after=session_after,
        root_seed=root_seed,
        episode_index=EPISODE_908_INDEX,
        stream_index=stream_index,
        game_seed=episode.game_seed,
        episode_sha256=sha256(episode.to_json().encode("utf-8")).hexdigest(),
        terminal_status=episode.status.value,
        environment_transitions=episode.action_count,
        committed=False,
        target=target,
    )


def trace_checkpoint_search_subowners(
    root_seed: str | int,
    checkpoint_path: str | Path,
    *,
    clock: Callable[[], float] = perf_counter,
    environment_factory=make_ppo_training_environment,
    subowner_tracer=_trace_candidate_subowners,
    episode_collector=collect_complete_ppo_episode,
) -> PPOCheckpointSearchSubownerReport:
    """Attribute exact helpers, then replay to the complete terminal boundary."""
    if not callable(clock):
        raise TypeError("clock must be callable")
    if not all(callable(value) for value in (environment_factory, subowner_tracer, episode_collector)):
        raise TypeError("checkpoint search diagnostic dependencies must be callable")

    checkpoint_bytes, payload = _read_canonical_checkpoint(Path(checkpoint_path))
    training_run = PPOTrainingRun.from_seed(root_seed)
    session = _restore_session(training_run, payload, environment_factory)
    model = session.learner.model
    policy_sha256 = model.parameter_sha256
    stream_index = EPISODE_INDEX % PPO_TRAINING_CONTRACT.parallel_environments
    if session.learner.assembler.next_episode_indices[stream_index] != EPISODE_INDEX:
        raise PPOContractError("checkpoint search target is not the pending stream index")
    session_before = sha256(_canonical_bytes(session.serialize())).hexdigest()

    scoped = subowner_tracer(
        episode_index=EPISODE_INDEX,
        target_index=TARGET_DECISION_INDEX,
        expected_prefix=EXPECTED_PREFIX,
        root_seed=root_seed,
        clock=clock,
        environment=environment_factory(stream_index),
        policy=model.infer,
        helper_scope="search_evaluation",
    )
    if not isinstance(scoped, _PPOTacticalScopedSubownerTrace):
        raise PPOContractError("checkpoint search diagnostic returned invalid scope")
    target = scoped.report
    if (
        target.verified_prefix_decisions != len(EXPECTED_PREFIX)
        or target.target_decision_index != TARGET_DECISION_INDEX
        or (
            target.public_input_sha256,
            target.action,
            target.selected_hand_indices,
            target.search_attempts,
        )
        != EXPECTED_PREFIX[-1]
    ):
        raise PPOContractError("checkpoint search target provenance drifted")

    episode = episode_collector(
        environment_factory(stream_index),
        training_run,
        episode_index=EPISODE_INDEX,
        policy=model.infer,
    )
    if model.parameter_sha256 != policy_sha256:
        raise PPOContractError("checkpoint search diagnostic policy changed")
    session_after = sha256(_canonical_bytes(session.serialize())).hexdigest()
    if session_after != session_before:
        raise PPOContractError("checkpoint search diagnostic mutated campaign state")
    if (
        episode.training_run != training_run
        or episode.episode_index != EPISODE_INDEX
        or episode.game_seed != training_run.game_seed(EPISODE_INDEX)
        or episode.truncated
        or not episode.status.terminal
    ):
        raise PPOContractError("checkpoint search terminal episode provenance drifted")
    timings = (
        scoped.search_evaluation_elapsed_seconds,
        scoped.policy_arbitration_elapsed_seconds,
        scoped.other_elapsed_seconds,
        scoped.residual_search_evaluation_elapsed_seconds,
        scoped.estimate_state_deepcopy_elapsed_seconds,
        scoped.residual_estimate_state_deepcopy_elapsed_seconds,
    )
    if any(not math.isfinite(value) or value < 0.0 for value in timings):
        raise PPOContractError("checkpoint search diagnostic timing is invalid")
    deepcopy_cost = next(
        (
            item
            for item in target.helper_costs
            if item.name == "_estimate_state_deepcopy"
        ),
        None,
    )
    if (
        deepcopy_cost is None
        or deepcopy_cost.calls != scoped.estimate_state_deepcopy_calls
        or abs(
            deepcopy_cost.exclusive_elapsed_seconds
            - scoped.estimate_state_deepcopy_elapsed_seconds
        )
        > 1e-9
        or sum(
            item.calls for item in scoped.estimate_state_deepcopy_callsites
        )
        != scoped.estimate_state_deepcopy_calls
        or abs(
            sum(
                item.exclusive_elapsed_seconds
                for item in scoped.estimate_state_deepcopy_callsites
            )
            - scoped.estimate_state_deepcopy_elapsed_seconds
        )
        > 1e-9
        or scoped.residual_estimate_state_deepcopy_elapsed_seconds > 1e-9
    ):
        raise PPOContractError(
            "checkpoint estimator deepcopy call-site accounting drifted"
        )

    return PPOCheckpointSearchSubownerReport(
        schema=PPO_CHECKPOINT_SEARCH_SUBOWNER_SCHEMA,
        campaign_version=PPO_CAMPAIGN_VERSION,
        checkpoint_sha256=sha256(checkpoint_bytes).hexdigest(),
        training_run_sha256=training_run.sha256,
        policy_parameter_sha256=policy_sha256,
        session_sha256_before=session_before,
        session_sha256_after=session_after,
        root_seed=root_seed,
        episode_index=EPISODE_INDEX,
        stream_index=stream_index,
        game_seed=episode.game_seed,
        episode_sha256=sha256(episode.to_json().encode("utf-8")).hexdigest(),
        terminal_status=episode.status.value,
        environment_transitions=episode.action_count,
        committed=False,
        search_evaluation_elapsed_seconds=scoped.search_evaluation_elapsed_seconds,
        policy_arbitration_elapsed_seconds=scoped.policy_arbitration_elapsed_seconds,
        other_elapsed_seconds=scoped.other_elapsed_seconds,
        residual_search_evaluation_elapsed_seconds=(
            scoped.residual_search_evaluation_elapsed_seconds
        ),
        estimate_state_deepcopy_calls=scoped.estimate_state_deepcopy_calls,
        estimate_state_deepcopy_elapsed_seconds=(
            scoped.estimate_state_deepcopy_elapsed_seconds
        ),
        estimate_state_deepcopy_callsites=(
            scoped.estimate_state_deepcopy_callsites
        ),
        residual_estimate_state_deepcopy_elapsed_seconds=(
            scoped.residual_estimate_state_deepcopy_elapsed_seconds
        ),
        target=target,
    )


def write_checkpoint_search_subowner_report(
    path: str | Path, report: PPOCheckpointSearchSubownerReport
) -> str:
    if not isinstance(report, PPOCheckpointSearchSubownerReport):
        raise TypeError("report must be PPOCheckpointSearchSubownerReport")
    destination = Path(path)
    if not destination.parent.is_dir():
        raise PPOContractError("checkpoint search report directory does not exist")
    content = report.to_json().encode("utf-8")
    _atomic_write(destination, content)
    return sha256(content).hexdigest()


def write_checkpoint_candidate_subowner_report(
    path: str | Path, report: PPOCheckpointCandidateSubownerReport
) -> str:
    if not isinstance(report, PPOCheckpointCandidateSubownerReport):
        raise TypeError("report must be PPOCheckpointCandidateSubownerReport")
    destination = Path(path)
    if not destination.parent.is_dir():
        raise PPOContractError("checkpoint candidate report directory does not exist")
    content = report.to_json().encode("utf-8")
    _atomic_write(destination, content)
    return sha256(content).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-seed", required=True)
    parser.add_argument("--checkpoint-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument(
        "--episode-908-decision-13-candidate-subowners",
        action="store_true",
    )
    arguments = parser.parse_args(argv)
    if arguments.episode_908_decision_13_candidate_subowners:
        report = trace_checkpoint_candidate_subowners(
            arguments.root_seed, arguments.checkpoint_path
        )
        digest = write_checkpoint_candidate_subowner_report(
            arguments.output_path, report
        )
        print(json.dumps({
            "schema": report.schema,
            "output_path": str(Path(arguments.output_path)),
            "report_sha256": digest,
            "checkpoint_sha256": report.checkpoint_sha256,
            "policy_parameter_sha256": report.policy_parameter_sha256,
            "episode_sha256": report.episode_sha256,
            "episode_index": report.episode_index,
            "target_decision_index": report.target.target_decision_index,
            "candidate_generation_elapsed_seconds": (
                report.target.candidate_generation_elapsed_seconds
            ),
        }, sort_keys=True, separators=(",", ":")))
        return 0
    report = trace_checkpoint_search_subowners(
        arguments.root_seed, arguments.checkpoint_path
    )
    digest = write_checkpoint_search_subowner_report(arguments.output_path, report)
    print(json.dumps({
        "schema": report.schema,
        "output_path": str(Path(arguments.output_path)),
        "report_sha256": digest,
        "checkpoint_sha256": report.checkpoint_sha256,
        "policy_parameter_sha256": report.policy_parameter_sha256,
        "episode_sha256": report.episode_sha256,
        "episode_index": report.episode_index,
        "target_decision_index": report.target.target_decision_index,
        "search_evaluation_elapsed_seconds": report.search_evaluation_elapsed_seconds,
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
