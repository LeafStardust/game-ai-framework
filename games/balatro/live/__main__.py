import argparse

from games.balatro.live.balatrobot_bridge import BalatroBotBridge
from games.balatro.live.launcher import BalatroLaunchError, BalatroLauncher
from games.balatro.live.runner import BalatroLiveRunner


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a game-ai-framework agent against live Balatro."
    )
    parser.add_argument("--deck", default="RED")
    parser.add_argument("--stake", default="WHITE")
    parser.add_argument("--seed", default=None)
    parser.add_argument(
        "--endpoint",
        default=BalatroBotBridge.DEFAULT_ENDPOINT,
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=5000,
    )
    parser.add_argument("--balatro-dir", default=None)
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Require Balatro to already be running.",
    )
    parser.add_argument(
        "--launch-timeout",
        type=float,
        default=30.0,
    )
    args = parser.parse_args()

    bridge = BalatroBotBridge(endpoint=args.endpoint)

    if not bridge.is_connected():
        if args.no_launch:
            parser.error(
                f"BalatroBot API is not available at {args.endpoint}"
            )

        launcher = BalatroLauncher(
            endpoint=args.endpoint,
            balatro_dir=args.balatro_dir,
            fast=args.fast,
            headless=args.headless,
        )
        try:
            launcher.launch()
            launcher.wait_until_connected(
                bridge,
                timeout=args.launch_timeout,
            )
        except BalatroLaunchError as error:
            parser.error(str(error))

    runner = BalatroLiveRunner(bridge=bridge)
    runner.run(
        deck=args.deck.upper(),
        stake=args.stake.upper(),
        seed=args.seed,
        max_steps=args.max_steps,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
