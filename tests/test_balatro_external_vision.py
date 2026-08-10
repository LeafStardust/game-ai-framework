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


def _grid_frame(values, cell_width=20, height=40):
    width = len(values) * cell_width
    row = b"".join(
        bytes((value, value, value, 255)) * cell_width
        for value in values
    )
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
        bgra=row * height,
    )


def _add_grid_samples(recognizer, phase, samples):
    for values in samples:
        recognizer.add_template(
            recognizer.template_from_frame(
                phase,
                _grid_frame(values),
                columns=len(values),
                rows=1,
            )
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


def test_phase_recognizer_ranks_one_best_match_per_phase():
    recognizer = BalatroVisualPhaseRecognizer()
    recognizer.add_template(
        recognizer.template_from_frame(
            "BLIND_SELECT",
            _solid_frame(200, 20, 20),
            columns=4,
            rows=3,
        )
    )
    recognizer.add_template(
        recognizer.template_from_frame(
            "BLIND_SELECT",
            _solid_frame(190, 25, 25),
            columns=4,
            rows=3,
        )
    )
    recognizer.add_template(
        recognizer.template_from_frame(
            "SHOP",
            _solid_frame(20, 20, 200),
            columns=4,
            rows=3,
        )
    )

    ranking = recognizer.rank(_solid_frame(195, 22, 22))

    assert [item.phase for item in ranking] == ["BLIND_SELECT", "SHOP"]
    assert ranking[0].distance < ranking[1].distance


def test_phase_recognizer_weights_stable_discriminative_cells_symmetrically():
    recognizer = BalatroVisualPhaseRecognizer()
    blind_samples = [
        [200, 0, 0, 100, 100, 0, 0, 100, 100],
        [200, 100, 100, 0, 0, 100, 100, 0, 0],
    ]
    hand_samples = [
        [50, 0, 0, 0, 0, 100, 100, 100, 100],
        [50, 100, 100, 100, 100, 0, 0, 0, 0],
    ]

    _add_grid_samples(recognizer, "BLIND_SELECT", blind_samples)
    _add_grid_samples(recognizer, "SELECTING_HAND", hand_samples)

    blind_ranking = recognizer.rank(
        _grid_frame([190, 0, 0, 0, 0, 100, 100, 100, 100])
    )
    hand_ranking = recognizer.rank(
        _grid_frame([55, 0, 0, 100, 100, 0, 0, 0, 0])
    )

    assert [item.phase for item in blind_ranking] == [
        "BLIND_SELECT",
        "SELECTING_HAND",
    ]
    assert [item.phase for item in hand_ranking] == [
        "SELECTING_HAND",
        "BLIND_SELECT",
    ]


def test_phase_recognizer_pairwise_voting_ignores_unrelated_global_color():
    recognizer = BalatroVisualPhaseRecognizer()
    _add_grid_samples(
        recognizer,
        "BLIND_SELECT",
        ([220, 20, 20, 20, 20, 20], [230, 30, 30, 30, 30, 30]),
    )
    _add_grid_samples(
        recognizer,
        "SELECTING_HAND",
        ([60, 20, 20, 20, 20, 20], [70, 30, 30, 30, 30, 30]),
    )
    _add_grid_samples(
        recognizer,
        "ROUND_EVAL",
        ([20, 220, 20, 20, 20, 20], [30, 230, 30, 30, 30, 30]),
    )
    _add_grid_samples(
        recognizer,
        "SHOP",
        ([20, 20, 220, 20, 20, 20], [30, 30, 230, 30, 30, 30]),
    )

    blind = recognizer.detect(_grid_frame([255, 100, 100, 100, 100, 100]))
    hand = recognizer.detect(_grid_frame([140, 100, 100, 100, 100, 100]))

    assert blind.phase == "BLIND_SELECT"
    assert blind.wins == 3.0
    assert hand.phase == "SELECTING_HAND"
    assert hand.wins == 3.0


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
