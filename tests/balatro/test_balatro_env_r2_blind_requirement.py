import pytest

from games.balatro.env.blind_requirement import (
    BlindRequirementError,
    red_white_base_blind_amount,
)


def test_env_r2_red_white_base_blind_amount_pins_ante_one_to_eight():
    assert [red_white_base_blind_amount(ante) for ante in range(1, 9)] == [
        300,
        800,
        2_000,
        5_000,
        11_000,
        20_000,
        35_000,
        50_000,
    ]


def test_env_r2_red_white_base_blind_amount_pins_preante_vanilla_floor():
    assert red_white_base_blind_amount(0) == 100
    assert red_white_base_blind_amount(-1) == 100
    assert red_white_base_blind_amount(-100) == 100


def test_env_r2_red_white_base_blind_amount_rejects_noninteger_and_unowned_endless():
    for value in (True, 1.5, "1", None):
        with pytest.raises(BlindRequirementError, match="exact integer"):
            red_white_base_blind_amount(value)  # type: ignore[arg-type]

    with pytest.raises(BlindRequirementError, match="beyond Ante 8"):
        red_white_base_blind_amount(9)
