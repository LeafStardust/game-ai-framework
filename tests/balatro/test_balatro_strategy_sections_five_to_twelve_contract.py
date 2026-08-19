from types import SimpleNamespace
from pathlib import Path

from games.balatro.strategy import BANNED, BRONZE, GOLD, NEUTRAL, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import conditional_joker_relationship
from games.balatro.strategy_tree_catalog import (
    REMAINING_SECTION_NODE_IDS,
    SECTION_EIGHT_NODE_IDS,
    SECTION_ELEVEN_NODE_IDS,
    SECTION_FIVE_NODE_IDS,
    SECTION_NINE_NODE_IDS,
    SECTION_SEVEN_NODE_IDS,
    SECTION_SIX_NODE_IDS,
    SECTION_TEN_NODE_IDS,
    SECTION_TWELVE_NODE_IDS,
    TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
)
from games.balatro.strategy_tree_tracker import TreeAwareStateAwareBalatroStrategyTracker


def _joker(class_name, **fields):
    item = type(class_name, (), {})()
    for name, value in fields.items():
        setattr(item, name, value)
    return item


def _card(rank, suit, *, enhancement="", seal=""):
    return SimpleNamespace(
        rank=rank,
        suit=suit,
        enhancement=enhancement,
        seal=seal,
        edition="",
    )


def _natural_deck():
    return [
        _card(rank, suit)
        for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
        for rank in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    ]


def _state(*, jokers=(), seal="", enhancement="", vouchers=(), consumables=(), money=30):
    deck = _natural_deck()
    if seal:
        deck[0].seal = seal
    if enhancement:
        deck[0].enhancement = enhancement
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=list(vouchers),
        consumables=list(consumables),
        owned_deck=deck,
        deck=deck,
        hand_levels={},
        hand_play_counts={},
        ante=4,
        money=money,
    )


def _tracker():
    return TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )


def test_sections_five_to_twelve_complete_the_frozen_runtime_forest():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY

    assert len(SECTION_FIVE_NODE_IDS) == 6
    assert len(SECTION_SIX_NODE_IDS) == 16
    assert len(SECTION_SEVEN_NODE_IDS) == 7
    assert len(SECTION_EIGHT_NODE_IDS) == 13
    assert len(SECTION_NINE_NODE_IDS) == 10
    assert len(SECTION_TEN_NODE_IDS) == 4
    assert len(SECTION_ELEVEN_NODE_IDS) == 11
    assert len(SECTION_TWELVE_NODE_IDS) == 4
    assert len(REMAINING_SECTION_NODE_IDS) == 71
    assert len(topology.nodes) == 136
    assert len(RUNTIME_UNIVERSAL_BALATRO_STRATEGIES) == 136
    assert all(
        len(topology.children_by_id[strategy_id]) != 1
        for strategy_id in REMAINING_SECTION_NODE_IDS
    )
    assert "edition" not in topology.nodes
    assert "edition" not in RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


def test_section_five_seal_support_is_neutral_until_matching_seal_exists():
    chad = _joker("HangingChadJoker")
    mime = _joker("MimeJoker")
    constellation = _joker("ConstellationJoker")

    assert conditional_joker_relationship(_state(), "red_seal_played", chad) == NEUTRAL
    assert conditional_joker_relationship(_state(seal="Red"), "red_seal_played", chad) == GOLD
    assert conditional_joker_relationship(_state(seal="Red"), "red_seal_held", mime) == NEUTRAL
    assert (
        conditional_joker_relationship(
            _state(seal="Red", enhancement="Steel"), "red_seal_held", mime
        )
        == GOLD
    )
    assert conditional_joker_relationship(_state(), "blue_seal", constellation) == NEUTRAL
    assert conditional_joker_relationship(_state(seal="Blue"), "blue_seal", constellation) == GOLD


def test_section_six_combo_leaves_require_their_defining_engine():
    trading = _joker("TradingCardJoker")
    canio = _joker("CanioJoker", x_mult=1.0)
    vampire = _joker("VampireJoker")
    midas = _joker("MidasMaskJoker")

    assert conditional_joker_relationship(_state(jokers=(trading,)), "canio_trading", trading) == NEUTRAL
    assert conditional_joker_relationship(_state(jokers=(canio,)), "canio_trading", trading) == GOLD
    assert conditional_joker_relationship(_state(jokers=(midas,)), "vampire_midas", midas) == NEUTRAL
    assert conditional_joker_relationship(_state(jokers=(vampire,)), "vampire_midas", midas) == GOLD

    solo = _state(jokers=(canio, _joker("MadnessJoker")))
    assert conditional_joker_relationship(solo, "madness_solo", solo.jokers[1]) == NEUTRAL
    eternal = _joker("FlatMultJoker", eternal=True)
    madness = _joker("MadnessJoker")
    assert conditional_joker_relationship(
        _state(jokers=(madness, eternal)), "madness_eternal", eternal
    ) == GOLD

    dagger = _joker("DaggerJoker")
    assert conditional_joker_relationship(
        _state(jokers=(dagger,)), "dagger_sacrifice", eternal
    ) == BANNED


def test_section_seven_growth_partner_does_not_seed_without_hologram():
    dna = _joker("DNAJoker")
    hologram = _joker("HologramJoker")

    assert conditional_joker_relationship(_state(jokers=(dna,)), "hologram_dna", dna) == NEUTRAL
    assert conditional_joker_relationship(_state(jokers=(hologram,)), "hologram_dna", dna) == GOLD


def test_section_eight_combo_and_part_fourteen_astronomer_support():
    constellation = _joker("ConstellationJoker")
    satellite = _joker("SatelliteJoker")
    astronomer = _joker("AstronomerJoker")
    state = _state(jokers=(constellation, satellite))

    assert conditional_joker_relationship(
        state, "planet_constellation_satellite", constellation
    ) == GOLD
    assert conditional_joker_relationship(
        _state(jokers=(constellation,)), "planet_constellation", astronomer
    ) == SILVER

    vagabond = _joker("VagabondJoker")
    bull = _joker("BullJoker")
    assert conditional_joker_relationship(
        _state(jokers=(vagabond,)), "vagabond", bull
    ) == BANNED


def test_section_nine_cash_combo_and_chaos_reroll_support_are_contextual():
    bull = _joker("BullJoker")
    bootstraps = _joker("BootstrapsJoker")
    chaos = _joker("ChaosTheClownJoker")
    flash = _joker("FlashCardJoker")

    state = _state(jokers=(bull, bootstraps))
    assert conditional_joker_relationship(state, "cash_bull_bootstraps", bull) == GOLD
    assert conditional_joker_relationship(_state(), "flash_card", chaos) == NEUTRAL
    assert conditional_joker_relationship(_state(jokers=(flash,)), "flash_card", chaos) == GOLD


def test_section_ten_board_relationships_obey_slot_direction():
    stencil = _joker("JokerStencil")
    riff_raff = _joker("RiffRaffJoker")
    baseball = _joker("BaseballCardJoker")
    uncommon = _joker("FlatMultJoker", rarity="Uncommon")
    showman = _joker("ShowmanJoker")
    invisible = _joker("InvisibleJoker")

    assert conditional_joker_relationship(
        _state(jokers=(stencil,)), "joker_stencil", riff_raff
    ) == BANNED
    assert conditional_joker_relationship(
        _state(jokers=(baseball,)), "baseball_card", uncommon
    ) == SILVER
    assert conditional_joker_relationship(
        _state(jokers=(baseball,)), "baseball_card", showman
    ) == SILVER
    assert conditional_joker_relationship(
        _state(jokers=(stencil,)), "joker_stencil", invisible
    ) == SILVER


def test_section_eleven_discard_and_no_discard_routes_conflict_materially():
    green = _joker("GreenJoker")
    trading = _joker("TradingCardJoker")
    burglar = _joker("BurglarJoker")
    castle = _joker("CastleJoker")
    drunkard = _joker("DrunkardJoker")

    assert conditional_joker_relationship(
        _state(jokers=(green,)), "no_discard_green", trading
    ) == BANNED
    assert conditional_joker_relationship(
        _state(jokers=(green,)), "no_discard_green", burglar
    ) == GOLD
    assert conditional_joker_relationship(
        _state(jokers=(castle,)), "discard_castle", drunkard
    ) == SILVER


def test_section_twelve_and_part_fourteen_copy_support_require_a_real_core():
    dusk = _joker("DuskJoker")
    chad = _joker("HangingChadJoker")
    blueprint = _joker("BlueprintJoker")
    acrobat = _joker("AcrobatJoker")

    assert conditional_joker_relationship(_state(), "last_hand_dusk", chad) == NEUTRAL
    assert conditional_joker_relationship(_state(jokers=(dusk,)), "last_hand_dusk", chad) == SILVER
    assert conditional_joker_relationship(_state(), "last_hand_acrobat", blueprint) == NEUTRAL
    assert conditional_joker_relationship(
        _state(jokers=(acrobat,)), "last_hand_acrobat", blueprint
    ) == SILVER


def test_part_fourteen_space_and_splash_support_slot_into_existing_routes():
    splash = _joker("SplashJoker")
    juggler = _joker("JugglerJoker")
    troubadour = _joker("TroubadourJoker")

    assert conditional_joker_relationship(
        _state(seal="Red"), "red_seal_played", splash
    ) == SILVER
    assert conditional_joker_relationship(
        _state(enhancement="Steel"), "steel_mime", juggler
    ) == SILVER
    assert conditional_joker_relationship(
        _state(seal="Blue"), "blue_seal", troubadour
    ) == BRONZE


def test_red_white_root_modifier_is_inherited_across_the_completed_tree():
    tracker = TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
        modifier_provider=lambda state: {
            "strategies": {"cash_hoard": {"effectiveness": 0.75}}
        },
    )

    assert tracker.effectiveness(_state(), "cash_bull_bootstraps") == 0.75
    assert tracker.effectiveness(_state(), "last_hand_dusk") == 1.0


def test_inverse_component_index_is_generated_from_the_full_tree_catalogue():
    tracker = _tracker()

    assert ("campfire", GOLD) in tracker.component_index["JOKER"]["campfirejoker"]
    assert ("blue_seal", GOLD) in tracker.component_index["CONSUMABLE"]["trance"]


def test_sections_five_to_twelve_parent_child_static_components_are_disjoint():
    definitions = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY

    for parent_id in REMAINING_SECTION_NODE_IDS:
        parent = definitions[parent_id]
        for child_id in topology.children_by_id[parent_id]:
            child = definitions[child_id]
            for kind in ("JOKER", "CONSUMABLE", "PLANET", "VOUCHER"):
                parent_components = set().union(
                    *(components for _, components in parent._buckets(kind))
                )
                child_components = set().union(
                    *(components for _, components in child._buckets(kind))
                )
                assert parent_components.isdisjoint(child_components)
            assert parent.directed_tarots.isdisjoint(child.directed_tarots)
            assert parent.directed_spectrals.isdisjoint(child.directed_spectrals)


def test_full_tree_tracker_resolves_a_late_section_leaf():
    campfire = _joker("CampfireJoker")
    resolution = _tracker().observe(_state(jokers=(campfire,)))

    assert resolution.assessment("campfire").score >= 8.0
    assert resolution.dominant_strategy_id == "campfire"


def test_relationship_document_has_no_unaudited_rows_and_part_fourteen_is_integrated():
    root = Path(__file__).resolve().parents[2]
    relationships = (root / "BALATRO_STRATEGY_RELATIONSHIPS.md").read_text(encoding="utf-8")
    topology = (root / "BALATRO_STRATEGY_TREE.md").read_text(encoding="utf-8")

    assert not any("TBD" in line for line in relationships.splitlines() if line.startswith("|"))
    for component in (
        "Blueprint / Brainstorm",
        "Astronomer",
        "Chaos the Clown",
        "Drunkard / Merry Andy",
        "Juggler / Troubadour",
        "Splash",
        "Showman",
        "Invisible Joker",
    ):
        assert f"| {component} |" in topology

    assert "Gold Seal Economy [I]" not in topology
    assert "Ceremonial Dagger Sacrifice [I]" not in topology
