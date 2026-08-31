from __future__ import annotations

from games.balatro.red_white_semantic_boss_native_cases import (
    RED_WHITE_BOSS_NATIVE_CASES,
)
from games.balatro.red_white_semantic_build_native_cases import (
    RED_WHITE_NATIVE_BUILD_CASES,
)
from games.balatro.red_white_semantic_cases import RED_WHITE_SEMANTIC_CASES
from games.balatro.red_white_semantic_d1_resource_cases import (
    RED_WHITE_D1_RESOURCE_CASES,
)
from games.balatro.red_white_semantic_phase1_d1_cases import (
    RED_WHITE_PHASE1_D1_CASES,
)
from games.balatro.red_white_semantic_phase2_cross_family_cases import (
    RED_WHITE_PHASE2_CROSS_FAMILY_CASES,
)
from games.balatro.red_white_semantic_phase2_shop_cases import (
    RED_WHITE_PHASE2_SHOP_CASES,
)
from games.balatro.red_white_semantic_shop_authority_cases import (
    RED_WHITE_SHOP_AUTHORITY_CASES,
)
from games.balatro.red_white_semantic_shop_native_cases import (
    RED_WHITE_NATIVE_SHOP_CASES,
)
from games.balatro.semantic_benchmark import run_semantic_benchmark


def run():
    return run_semantic_benchmark(
        (
            *RED_WHITE_SEMANTIC_CASES,
            *RED_WHITE_D1_RESOURCE_CASES,
            *RED_WHITE_SHOP_AUTHORITY_CASES,
            *RED_WHITE_NATIVE_SHOP_CASES,
            *RED_WHITE_NATIVE_BUILD_CASES,
            *RED_WHITE_BOSS_NATIVE_CASES,
            *RED_WHITE_PHASE1_D1_CASES,
            *RED_WHITE_PHASE2_SHOP_CASES,
            *RED_WHITE_PHASE2_CROSS_FAMILY_CASES,
        )
    )


def main() -> int:
    report = run()
    print(report.render())
    return 0 if not report.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
