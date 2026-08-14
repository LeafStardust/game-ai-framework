import pytest

from games.balatro.live.external.live_memory_restart_contract import (
    start_run_source_matches,
)


def test_start_run_source_matches_preserve_numbered_context():
    source = "\n".join(
        (
            "alpha",
            "beta",
            "G.FUNCS.start_run = function(e, args)",
            "  return G:start_run(args)",
            "end",
            "omega",
        )
    )

    matches = start_run_source_matches(source, context_lines=1)

    assert [match.line_number for match in matches] == [3, 4]
    assert matches[0].lines == (
        "000002: beta",
        "000003: G.FUNCS.start_run = function(e, args)",
        "000004:   return G:start_run(args)",
    )
    assert matches[1].lines == (
        "000003: G.FUNCS.start_run = function(e, args)",
        "000004:   return G:start_run(args)",
        "000005: end",
    )


def test_start_run_source_matches_respect_limit_and_validate_arguments():
    source = "start_run one\nstart_run two\nstart_run three"

    matches = start_run_source_matches(source, context_lines=0, max_matches=2)

    assert [match.line_number for match in matches] == [1, 2]
    with pytest.raises(ValueError, match="context_lines"):
        start_run_source_matches(source, context_lines=-1)
    with pytest.raises(ValueError, match="max_matches"):
        start_run_source_matches(source, max_matches=0)
