import argparse

from games.balatro.live.balatrobot_bridge import BalatroBotBridge
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
    args = parser.parse_args()

    bridge = BalatroBotBridge(endpoint=args.endpoint)
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
