"""Opt-in preservation of settled public SELL_JOKER parity fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from games.balatro.actions import SELL_JOKER
from games.balatro.live.parity_capture import (
    successful_joker_sale_evidence_from_run_rows,
)
from games.balatro.live.purchase_fixture import (
    PurchaseFixtureError,
    preserve_successful_purchase_fixture,
)


JokerSaleFixtureError = PurchaseFixtureError


def preserve_successful_joker_sale_fixture(
    source: str | Path,
    destination: str | Path,
    *,
    occurrence: int = 0,
    overwrite: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Preserve one validated SELL_JOKER boundary using original run-log rows."""
    return preserve_successful_purchase_fixture(
        source,
        destination,
        action_name=SELL_JOKER,
        evidence_parser=successful_joker_sale_evidence_from_run_rows,
        occurrence=occurrence,
        overwrite=overwrite,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preserve one successful canonical SELL_JOKER transition from a "
            "balatro-run-experience-v1 JSONL log for deterministic R5 replay."
        )
    )
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--occurrence", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    rows = preserve_successful_joker_sale_fixture(
        args.source,
        args.destination,
        occurrence=args.occurrence,
        overwrite=args.overwrite,
    )
    action = rows[1]["data"]["action"]
    target = action.get("target", {})
    print(
        "Preserved SELL_JOKER fixture -> "
        f"{args.destination} (joker_index={target.get('joker_index', 'unknown')})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
