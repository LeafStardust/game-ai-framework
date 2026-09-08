from types import SimpleNamespace

from games.balatro.actions import BUY_VOUCHER, BalatroAction
from games.balatro.live.run_experience_transition import build_rationale_log_payload


def test_d3_voucher_notes_are_classified_as_build_rationale():
    decision = SimpleNamespace(
        action=BalatroAction(
            BUY_VOUCHER,
            target=SimpleNamespace(label="Antimatter", price=10),
        ),
        source="shop policy",
        notes=(
            "policy_score=9.250000",
            "D3 voucher=Antimatter",
            "D3 build compatibility=1.500",
            "D3 Antimatter Joker-capacity pressure=0 free_slots=5",
            "D3 purchase advantage=8.900",
        ),
    )

    payload = build_rationale_log_payload(decision)

    assert payload is not None
    assert payload["action_family"] == "PURCHASE"
    assert [signal["kind"] for signal in payload["signals"]] == [
        "D3",
        "D3",
        "D3",
        "D3",
    ]
    assert all(
        signal["text"] != "policy_score=9.250000"
        for signal in payload["signals"]
    )
