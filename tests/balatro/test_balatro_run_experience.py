import json

from games.balatro.live.run_experience import (
    BalatroRunExperienceLogger,
    BalatroRunIdentity,
)


def test_run_experience_appends_ordered_jsonl(tmp_path):
    run = BalatroRunIdentity.create(
        deck="red",
        stake="white",
        playbook="red-white",
        playbook_version="1",
    )
    logger = BalatroRunExperienceLogger(run, directory=tmp_path)

    logger.run_started(state={"ante": 1})
    logger.decision(
        action={"name": "SELECT_BLIND", "target": "SMALL"},
        rationale={"policy": "playbook"},
    )
    logger.run_finished(won=False, state={"ante": 1}, reason="loss")

    rows = [json.loads(line) for line in logger.path.read_text().splitlines()]
    assert [row["sequence"] for row in rows] == [1, 2, 3]
    assert [row["event"] for row in rows] == [
        "run_started",
        "decision",
        "run_finished",
    ]
    assert all(row["run_id"] == run.run_id for row in rows)
    assert all(row["deck"] == "RED" for row in rows)
    assert all(row["stake"] == "WHITE" for row in rows)
    assert rows[1]["data"]["rationale"]["policy"] == "playbook"
    assert rows[2]["data"]["won"] is False


def test_run_experience_rejects_empty_event(tmp_path):
    run = BalatroRunIdentity.create(
        deck="RED",
        stake="WHITE",
        playbook="red-white",
    )
    logger = BalatroRunExperienceLogger(run, directory=tmp_path)

    try:
        logger.record("   ")
    except ValueError as error:
        assert "cannot be empty" in str(error)
    else:
        raise AssertionError("empty event should be rejected")
