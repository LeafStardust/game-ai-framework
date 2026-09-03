import pytest

from games.balatro.env.rng import (
    BALATRO_RNG_VERSION,
    BalatroRNG,
    LuaJITRandom,
    pseudohash,
)


def test_balatro_rng_pseudohash_reference_vectors():
    assert pseudohash("") == 1.0
    assert pseudohash("TESTSEED") == 0.3192720782223546
    assert pseudohash("ABCDEFGH") == 0.07496421241671669


def test_balatro_rng_luajit_reference_vector():
    rng = LuaJITRandom(pseudohash("TESTSEED"))

    assert [rng.random() for _ in range(5)] == [
        0.46679072846167013,
        0.2652965733779933,
        0.20574006575360015,
        0.4541739727552512,
        0.9446052267728067,
    ]


def test_balatro_rng_keyed_queue_reference_vector():
    rng = BalatroRNG("TESTSEED")

    assert [rng.random("shuffle1") for _ in range(3)] == [
        0.3203278531352878,
        0.4737515523801965,
        0.12180226138499406,
    ]
    assert rng.nodes["shuffle1"] == 0.7746237972943


def test_balatro_rng_different_keys_advance_independently():
    interleaved = BalatroRNG("TESTSEED")
    first_a = interleaved.random("shuffle1")
    first_b = interleaved.random("Joker11")
    second_a = interleaved.random("shuffle1")
    second_b = interleaved.random("Joker11")

    assert (first_a, second_a) == (
        0.3203278531352878,
        0.4737515523801965,
    )
    assert (first_b, second_b) == (
        0.8977596248957909,
        0.18048116001175196,
    )


def test_balatro_rng_snapshot_restore_preserves_next_result_exactly():
    original = BalatroRNG("TESTSEED")
    original.random("shuffle1")
    original.random("Joker11")

    snapshot = original.snapshot()
    restored = BalatroRNG.from_snapshot(snapshot)

    assert snapshot["version"] == BALATRO_RNG_VERSION
    assert restored.snapshot() == snapshot
    assert restored.random("shuffle1") == original.random("shuffle1")
    assert restored.random("Joker11") == original.random("Joker11")


def test_balatro_rng_snapshot_rejects_unknown_version():
    with pytest.raises(ValueError, match="unsupported Balatro RNG snapshot version"):
        BalatroRNG.from_snapshot(
            {"version": "future", "seed": "TESTSEED", "nodes": {}}
        )


def test_balatro_rng_rejects_unowned_unkeyed_seed_stream():
    rng = BalatroRNG("TESTSEED")

    with pytest.raises(ValueError, match="unkeyed 'seed' randomness is not owned"):
        rng.random("seed")


def test_balatro_rng_randint_is_inclusive_and_deterministic():
    a = BalatroRNG("TESTSEED")
    b = BalatroRNG("TESTSEED")

    values_a = [a.randint("deal", 1, 52) for _ in range(20)]
    values_b = [b.randint("deal", 1, 52) for _ in range(20)]

    assert values_a == values_b
    assert all(1 <= value <= 52 for value in values_a)
