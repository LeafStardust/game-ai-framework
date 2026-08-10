from games.balatro.live.external import (
    BalatroFrame,
    BalatroVisualPhaseRecognizer,
    BalatroWindow,
    ColorGridSignature,
    PhaseTemplate,
    UNKNOWN_PHASE,
    WindowRect,
)


def _solid_frame(red, green, blue, width=120, height=70):
    pixel = bytes((blue, green, red, 255))
    return BalatroFrame(
        sequence=1,
        timestamp=0.0,
        window=BalatroWindow(
            handle=1,
            title="Balatro",
            client_rect=WindowRect(0, 0, width, height),
        ),
        width=width,
        height=height,
        bgra=pixel * width * height,
    )


def test_phase_recognizer_matches_calibrated_external_frame():
    recognizer = BalatroVisualPhaseRecognizer()
    recognizer.add_template(
        recognizer.template_from_frame(
            "BLIND_SELECT",
            _solid_frame(200, 20, 20),
            columns=6,
            rows=4,
            max_distance=0.1,
        )
    )
    recognizer.add_template(
        recognizer.template_from_frame(
            "SHOP",
            _solid_frame(20, 20, 200),
            columns=6,
            rows=4,
            max_distance=0.1,
        )
    )

    detection = recognizer.detect(_solid_frame(195, 25, 20))

    assert detection.phase == "BLIND_SELECT"
    assert detection.confidence > 0.95


def test_phase_recognizer_returns_unknown_outside_threshold():
    recognizer = BalatroVisualPhaseRecognizer()
    recognizer.add_template(
        recognizer.template_from_frame(
            "SHOP",
            _solid_frame(0, 0, 255),
            columns=4,
            rows=3,
            max_distance=0.05,
        )
    )

    detection = recognizer.detect(_solid_frame(255, 255, 0))

    assert detection.phase == UNKNOWN_PHASE


def test_phase_template_serialization_round_trip():
    recognizer = BalatroVisualPhaseRecognizer()
    template = recognizer.template_from_frame(
        "SELECTING_HAND",
        _solid_frame(40, 80, 120),
        columns=3,
        rows=2,
    )

    restored = PhaseTemplate.from_dict(template.to_dict())

    assert restored == template
    assert isinstance(restored.signature, ColorGridSignature)
