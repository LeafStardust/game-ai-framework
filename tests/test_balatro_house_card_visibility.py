from games.balatro.live.external.card_templates import RGBImage
from games.balatro.live.external.house_card_visibility import is_face_up_image


def _solid_image(red: int, green: int, blue: int, *, width=80, height=120):
    pixel = bytes((red, green, blue))
    return RGBImage(width, height, pixel * (width * height))


def test_house_visibility_accepts_bright_neutral_playing_card_face():
    assert is_face_up_image(_solid_image(220, 220, 220)) is True


def test_house_visibility_rejects_saturated_card_back_without_neutral_face():
    assert is_face_up_image(_solid_image(80, 25, 25)) is False


def test_house_visibility_rejects_dark_card_back():
    assert is_face_up_image(_solid_image(40, 45, 55)) is False
