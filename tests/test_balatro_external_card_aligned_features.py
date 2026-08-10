from games.balatro.live.external.card_aligned_features import (
    aligned_rank_shape_signature,
    aligned_suit_color_signature,
    detect_card_face_top,
)
from games.balatro.live.external.card_templates import RGBImage


HEART = (241, 27, 82)
SPADE = (36, 44, 86)
BACKGROUND = (41, 88, 68)
FACE = (240, 240, 240)


def _card_image(
    *,
    face_top: int,
    color: tuple[int, int, int],
    rank: str = "single",
) -> RGBImage:
    width = 60
    height = 88
    pixels = bytearray(BACKGROUND * (width * height))

    for y in range(face_top, height):
        for x in range(4, width):
            _set_pixel(pixels, width, x, y, FACE)

    rank_top = face_top + 10
    if rank == "single":
        for y in range(rank_top, rank_top + 15):
            for x in range(10, 14):
                _set_pixel(pixels, width, x, y, color)
        for y in range(rank_top + 6, rank_top + 10):
            for x in range(10, 20):
                _set_pixel(pixels, width, x, y, color)
    elif rank == "double":
        for y in range(rank_top, rank_top + 15):
            for x in range(9, 12):
                _set_pixel(pixels, width, x, y, color)
            for x in range(16, 21):
                if y in range(rank_top, rank_top + 3) or y in range(rank_top + 12, rank_top + 15):
                    _set_pixel(pixels, width, x, y, color)
                _set_pixel(pixels, width, 16, y, color)
                _set_pixel(pixels, width, 20, y, color)
    else:
        raise ValueError(rank)

    suit_top = face_top + 29
    for y in range(suit_top, suit_top + 12):
        for x in range(12, 19):
            if abs(x - 15) + abs(y - (suit_top + 5)) <= 6:
                _set_pixel(pixels, width, x, y, color)

    return RGBImage(width, height, bytes(pixels))


def _set_pixel(
    pixels: bytearray,
    width: int,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    index = (y * width + x) * 3
    pixels[index : index + 3] = bytes(color)


def test_detect_card_face_top_tracks_hand_fan_offset():
    assert detect_card_face_top(_card_image(face_top=0, color=HEART)) == 0
    assert detect_card_face_top(_card_image(face_top=17, color=HEART)) == 17


def test_aligned_rank_shape_is_invariant_to_face_offset_and_suit_color():
    first = _card_image(face_top=0, color=HEART)
    shifted = _card_image(face_top=17, color=SPADE)

    first_color = aligned_suit_color_signature(first)
    shifted_color = aligned_suit_color_signature(shifted)
    first_rank = aligned_rank_shape_signature(
        first,
        first_color,
        columns=20,
        rows=20,
    )
    shifted_rank = aligned_rank_shape_signature(
        shifted,
        shifted_color,
        columns=20,
        rows=20,
    )

    assert first_rank == shifted_rank


def test_aligned_suit_color_tracks_glyph_color_after_face_alignment():
    heart = aligned_suit_color_signature(_card_image(face_top=17, color=HEART))
    spade = aligned_suit_color_signature(_card_image(face_top=0, color=SPADE))

    assert heart == HEART
    assert spade == SPADE


def test_aligned_rank_shape_keeps_two_component_rank_distinct():
    single = _card_image(face_top=17, color=HEART, rank="single")
    double = _card_image(face_top=0, color=SPADE, rank="double")

    single_signature = aligned_rank_shape_signature(
        single,
        aligned_suit_color_signature(single),
        columns=20,
        rows=20,
    )
    double_signature = aligned_rank_shape_signature(
        double,
        aligned_suit_color_signature(double),
        columns=20,
        rows=20,
    )

    assert single_signature != double_signature
