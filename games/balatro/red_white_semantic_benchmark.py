from __future__ import annotations

from games.balatro.red_white_semantic_cases import RED_WHITE_SEMANTIC_CASES
from games.balatro.red_white_semantic_d1_resource_cases import (
    RED_WHITE_D1_RESOURCE_CASES,
)
from games.balatro.semantic_benchmark import run_semantic_benchmark


def run():
    return run_semantic_benchmark(
        (*RED_WHITE_SEMANTIC_CASES, *RED_WHITE_D1_RESOURCE_CASES)
    )


def main() -> int:
    report = run()
    print(report.render())
    return 0 if not report.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
