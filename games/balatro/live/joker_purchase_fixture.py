"""Opt-in preservation of settled public BUY_JOKER parity fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from games.balatro.actions import BUY_JOKER
from games.balatro.live.parity_capture import (
    successful_joker_purchase_evidence_from_run_rows,
)
from games.balatro.live.purchase_fixture import (
    PurchaseFixtureError,
    preserve_successful_purchase_fixture,
)


JokerPurchaseFixtureError = PurchaseFixtureError


def preserve_successful_joker_purchase_fixture(
    source: str | Path,
    destination: str | Path,
    *,
    occurrence: int = 0,
    overwrite: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Preserve one validated BUY_JOKER boundary using original run-log rows."""
    return preserve_successful_purchase_fixture(
        source,
        destination,
        action_name=BUY_JOKER,
        evidence_parser=successful_joker_purchase_evidence_from_run_rows,
        occurrence=occurrence,
        overwrite=overwrite,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preserve one successful canonical BUY_JOKER transition from a "
            "balatro-run-experience-v1 JSONL log for deterministic R5 replay."
        )
    )
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--occurrence", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    rows = preserve_successful_joker_purchase_fixture(
        args.source,
        args.destination,
        occurrence=args.occurrence,
        overwrite=args.overwrite,
    )
    action = rows[1]["data"]["action"]
    print(
        "Preserved BUY_JOKER fixture -> "
        f"{args.destination} ({action.get('target', {}).get('label', 'unknown target')})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
