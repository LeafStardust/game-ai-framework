from types import SimpleNamespace

import games.balatro.build_health_policy as health_policy


def test_build_health_does_not_cancel_existing_approved_replacement(monkeypatch):
    class _Health:
        def evaluate(self, state, *, strategy_tracker=None):
            del state, strategy_tracker
            return SimpleNamespace(
                total=75.0,
                survival=90.0,
                immediate=90.0,
                scaling=70.0,
                coherence=70.0,
                runway=70.0,
                critical=False,
                scaling_deficit=False,
                warnings=(),
                engines=(),
            )

    monkeypatch.setattr(health_policy, "_HEALTH", _Health())
    policy = SimpleNamespace(
        transition_planner=SimpleNamespace(
            evaluator=SimpleNamespace(strategy_tracker=None)
        )
    )
    state = SimpleNamespace(
        ante=6,
        phase="SHOP",
        money=30,
        score=0,
        blind_score=20000,
        hands_remaining=0,
        discards_remaining=0,
        jokers=[SimpleNamespace(name="Incumbent")],
        joker_slots=1,
        hand_levels={},
        hand_play_counts={},
        owned_deck=[],
        deck=[],
    )
    option = SimpleNamespace(
        eligible=True,
        replace_index=0,
        total_advantage=2.0,
        build_delta=2.0,
        economics=SimpleNamespace(money_after=20),
    )
    decision = SimpleNamespace(
        action="REPLACE",
        selected=option,
        options=(option,),
        thresholds=SimpleNamespace(reserve_target=10),
        rationale=("replacement already approved",),
    )

    result = health_policy._health_aware_joker_decision(
        policy,
        state,
        SimpleNamespace(name="Candidate"),
        decision,
    )

    assert result is decision
    assert result.action == "REPLACE"
