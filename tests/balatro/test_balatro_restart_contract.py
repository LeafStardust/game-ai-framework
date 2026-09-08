import pytest

from games.balatro.live.external.live_memory_restart_contract import (
    archive_matches,
    source_matches,
    start_run_archive_matches,
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


def test_start_run_archive_matches_scan_multiple_lua_sources_with_global_limit():
    sources = {
        "main.lua": "loader only",
        "game.lua": "alpha\nG.FUNCS.start_run = function(e, args)\nomega",
        "functions/button_callbacks.lua": "before\nG.FUNCS.start_run({})\nafter",
    }

    matches = start_run_archive_matches(
        sources,
        context_lines=0,
        max_matches=2,
    )

    assert [(match.source_name, match.line_number) for match in matches] == [
        ("functions/button_callbacks.lua", 2),
        ("game.lua", 2),
    ]
    assert matches[0].lines == ("000002: G.FUNCS.start_run({})",)
    assert matches[1].lines == (
        "000002: G.FUNCS.start_run = function(e, args)",
    )


def test_arbitrary_source_pattern_can_probe_native_restart_button_contract():
    source = "\n".join(
        (
            "before",
            "UIBox_button{id = 'restart_button', button = 'start_run'}",
            "after",
        )
    )

    matches = source_matches(source, "restart_button", context_lines=1)

    assert len(matches) == 1
    assert matches[0].line_number == 2
    assert matches[0].lines == (
        "000001: before",
        "000002: UIBox_button{id = 'restart_button', button = 'start_run'}",
        "000003: after",
    )

    archive = archive_matches(
        {"functions/UI_definitions.lua": source, "main.lua": "loader"},
        "restart_button",
        context_lines=0,
    )
    assert [(match.source_name, match.line_number) for match in archive] == [
        ("functions/UI_definitions.lua", 2),
    ]

    with pytest.raises(ValueError, match="pattern"):
        source_matches(source, "")
    with pytest.raises(ValueError, match="pattern"):
        archive_matches({"main.lua": source}, "")
