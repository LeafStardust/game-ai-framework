from framework.config.config import FrameworkConfig


def test_default_config():
    config = FrameworkConfig()

    assert config.max_steps == 1000
    assert config.seed is None


def test_custom_config():
    config = FrameworkConfig(
        max_steps=50,
        seed=42
    )

    assert config.max_steps == 50
    assert config.seed == 42