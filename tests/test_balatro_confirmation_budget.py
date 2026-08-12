from games.balatro.live.adaptive_search import AdaptiveBlindSearchConfig
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine


def test_confirmation_strengthens_sampling_without_expanding_node_budget():
    engine = LiveHandActionDecisionEngine(max_search_nodes=5000)
    config = AdaptiveBlindSearchConfig(
        horizon=2,
        samples=8,
        child_samples=1,
        play_width=3,
        discard_width=1,
        child_play_width=1,
        child_discard_width=1,
        max_nodes=2000,
    )

    confirmation = engine._confirmation_config(config)

    assert confirmation.horizon == config.horizon
    assert confirmation.samples >= engine.CONFIRMATION_MIN_ROOT_SAMPLES
    assert confirmation.samples > config.samples
    assert confirmation.child_samples >= engine.CONFIRMATION_MIN_CHILD_SAMPLES
    assert confirmation.child_samples > config.child_samples
    assert confirmation.play_width == config.play_width
    assert confirmation.discard_width == config.discard_width
    assert confirmation.child_play_width == config.child_play_width
    assert confirmation.child_discard_width == config.child_discard_width
    assert confirmation.max_nodes == config.max_nodes
