import pytest

from games.balatro.env.transition import HeadlessTransitionError
from games.balatro.live import reroll_parity_checkpoint as checkpoint_module
from games.balatro.live.reroll_parity_checkpoint import LiveRerollParityCheckpointError
from tests.balatro.test_balatro_env_r5_reroll_replay import _fixture


def test_env_r5_reroll_replay_preserves_exact_headless_rejection_reason(monkeypatch):
    _, _, live_evidence, before_checkpoint, after_checkpoint, translator = _fixture()

    def reject(_run):
        raise HeadlessTransitionError("cannot afford paid shop reroll")

    monkeypatch.setattr(checkpoint_module, "reroll_shop_with_public_evidence", reject)

    with pytest.raises(
        LiveRerollParityCheckpointError,
        match="does not admit exact headless reroll replay: cannot afford paid shop reroll",
    ):
        checkpoint_module.compare_live_reroll_replay(
            before_checkpoint,
            after_checkpoint,
            live_evidence,
            translator=translator,
        )
