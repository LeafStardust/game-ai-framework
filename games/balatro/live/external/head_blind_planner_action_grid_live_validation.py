from __future__ import annotations

from . import head_blind_planner_action_live_validation as base
from .expected_card_locator import locate_card_faces_expected_count


def _grid_card_locator(expected_count: int):
    def locate(region):
        return locate_card_faces_expected_count(region, expected_count)

    return locate


def main() -> int:
    base._head_card_locator = _grid_card_locator
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
