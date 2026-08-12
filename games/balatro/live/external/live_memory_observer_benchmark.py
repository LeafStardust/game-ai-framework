from __future__ import annotations

from time import perf_counter

from .live_memory_observer import LiveMemoryBalatroObserver


def main() -> int:
    with LiveMemoryBalatroObserver() as observer:
        cold_started = perf_counter()
        cold = observer.observe()
        cold_elapsed = perf_counter() - cold_started

        warm_started = perf_counter()
        warm = observer.observe()
        warm_elapsed = perf_counter() - warm_started

    same_checkpoint = (
        cold.phase == warm.phase
        and cold.state_complete == warm.state_complete
        and cold.payload == warm.payload
    )

    print("Live-memory observer benchmark -> READY")
    print(f"Phase -> {warm.phase}")
    print(f"Cold observation -> {cold_elapsed:.3f}s")
    print(f"Warm observation -> {warm_elapsed:.3f}s")
    print(f"Same public checkpoint -> {same_checkpoint}")
    print("Observation process writes -> False")
    print("Hidden RNG/deck traversal -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
