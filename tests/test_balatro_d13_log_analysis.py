from games.balatro.live.runtime.d13_log_analysis import analyze_d13_rows


def _observation(sequence, *, ante, money, blind_type, tag):
    return {
        "schema": "balatro-run-experience-v1",
        "sequence": sequence,
        "event": "observation",
        "data": {
            "state": {
                "sequence": sequence,
                "phase": "BLIND_SELECT",
                "payload": {
                    "ante_num": ante,
                    "money": money,
                    "blind": {"type": blind_type, "tag": tag},
                },
            }
        },
    }


def _decision(sequence, *, action, margin, threshold, tag, blind_type="SMALL"):
    return {
        "schema": "balatro-run-experience-v1",
        "sequence": sequence,
        "event": "decision",
        "data": {
            "action": {"name": action},
            "rationale": {
                "decision_source": "D13 contextual blind play-vs-skip policy",
                "postmortem": {
                    "layer": "D13",
                    "selected": {
                        "action": action,
                        "blind_type": blind_type,
                        "tag_key": tag,
                        "build_readiness": 0.4,
                        "play_ev": 8.0,
                        "skip_ev": 8.0 + margin,
                        "margin": margin,
                        "threshold": threshold,
                    },
                },
            },
        },
    }


def test_d13_log_analysis_ranks_best_real_opportunity():
    rows = [
        _observation(1, ante=1, money=4, blind_type="SMALL", tag="tag_double"),
        _decision(2, action="SELECT_BLIND", margin=-3.5, threshold=2.0, tag="tag_double"),
        _observation(3, ante=3, money=18, blind_type="SMALL", tag="tag_economy"),
        _decision(4, action="SKIP_BLIND", margin=4.0, threshold=2.0, tag="tag_economy"),
    ]

    result = analyze_d13_rows(rows)

    assert result["d13_decision_count"] == 2
    assert result["executed_skip_count"] == 1
    assert result["skip_was_offered_by_policy"] is True
    assert result["policy_consistency_error_count"] == 0
    assert result["best_opportunity"]["ante"] == 3
    assert result["best_opportunity"]["tag_key"] == "tag_economy"
    assert result["best_opportunity"]["margin"] == 4.0


def test_d13_log_analysis_distinguishes_no_offer_from_failed_execution():
    rows = [
        _observation(1, ante=2, money=11, blind_type="BIG", tag="tag_handy"),
        _decision(2, action="SELECT_BLIND", margin=-0.86, threshold=2.0, tag="tag_handy", blind_type="BIG"),
    ]

    result = analyze_d13_rows(rows)

    assert result["executed_skip_count"] == 0
    assert result["skip_was_offered_by_policy"] is False
    assert result["best_opportunity"]["distance_to_skip"] == 2.86


def test_d13_log_analysis_flags_select_when_margin_should_skip():
    rows = [
        _observation(1, ante=3, money=20, blind_type="SMALL", tag="tag_economy"),
        _decision(2, action="SELECT_BLIND", margin=3.0, threshold=2.0, tag="tag_economy"),
    ]

    result = analyze_d13_rows(rows)

    assert result["skip_was_offered_by_policy"] is True
    assert result["executed_skip_count"] == 0
    assert result["policy_consistency_error_count"] == 1
