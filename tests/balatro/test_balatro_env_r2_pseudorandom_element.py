import pytest

from games.balatro.env.rng import BalatroRNG


def test_env_r2_pseudorandom_element_pins_cerulean_bell_testseed_vector():
    rng = BalatroRNG("TESTSEED")

    chosen = rng.pseudorandom_element_index(8, "cerulean_bell")

    # Vanilla pseudorandom_element sorts dense Lua-array numeric keys 1..n,
    # seeds math.random once from pseudoseed('cerulean_bell'), then performs one
    # math.random(n). For TESTSEED that draw is key 1 / zero-based index 0.
    assert chosen == 0
    assert rng.nodes["cerulean_bell"] == pytest.approx(0.2175606045966)


def test_env_r2_pseudorandom_element_advances_key_once_per_call():
    rng = BalatroRNG("TESTSEED")

    first = rng.pseudorandom_element_index(8, "cerulean_bell")
    first_node = rng.nodes["cerulean_bell"]
    second = rng.pseudorandom_element_index(8, "cerulean_bell")
    second_node = rng.nodes["cerulean_bell"]

    assert first == 0
    assert first_node == pytest.approx(0.2175606045966)
    assert second_node != first_node
    assert 0 <= second < 8


def test_env_r2_pseudorandom_element_snapshot_restore_preserves_next_choice():
    rng = BalatroRNG("TESTSEED")
    rng.pseudorandom_element_index(8, "cerulean_bell")
    snapshot = rng.snapshot()

    expected = rng.pseudorandom_element_index(8, "cerulean_bell")
    restored = BalatroRNG.from_snapshot(snapshot)

    assert restored.pseudorandom_element_index(8, "cerulean_bell") == expected
    assert restored.snapshot() == rng.snapshot()


def test_env_r2_pseudorandom_element_length_one_still_advances_key_once():
    rng = BalatroRNG("TESTSEED")

    assert rng.pseudorandom_element_index(1, "cerulean_bell") == 0
    assert "cerulean_bell" in rng.nodes


def test_env_r2_pseudorandom_element_rejects_invalid_lengths():
    rng = BalatroRNG("TESTSEED")

    for value in (True, 1.0, "8", None):
        with pytest.raises(TypeError, match="exact integer"):
            rng.pseudorandom_element_index(value, "cerulean_bell")

    for value in (0, -1):
        with pytest.raises(ValueError, match="non-empty"):
            rng.pseudorandom_element_index(value, "cerulean_bell")
