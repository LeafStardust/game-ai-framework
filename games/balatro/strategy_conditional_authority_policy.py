from __future__ import annotations

"""Make documented prerequisite relationships real downgrades.

The state-aware relationship layer historically allowed a conditional relationship
only to *upgrade* most static catalogue tiers.  Therefore a conditional resolver
returning NEUTRAL could fail to remove a static Silver/Gold relationship whose
prerequisite was absent.  This policy enumerates relationships whose tier is
explicitly state-dependent and lets the conditional resolver authoritatively
replace the static tier in both owned-build assessment and candidate evaluation.
"""

from games.balatro import strategy_conditional_relationships as conditional_module
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


def _tokens(*names: str) -> frozenset[str]:
    values = set()
    for name in names:
        token = "".join(ch for ch in name.lower() if ch.isalnum())
        if token:
            values.add(token if token.endswith("joker") else token + "joker")
    return frozenset(values)


def _positive_static_tokens(strategy_id: str) -> frozenset[str]:
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES[strategy_id]
    return frozenset(
        set(definition.gold_jokers)
        | set(definition.silver_jokers)
        | set(definition.bronze_jokers)
    )


def _build_authoritative_pairs() -> dict[str, frozenset[str]]:
    pairs: dict[str, set[str]] = {}

    def add(strategy_id: str, *names: str) -> None:
        pairs.setdefault(strategy_id, set()).update(_tokens(*names))

    # Poker-hand routes: generic repeat/support evidence is valid only after the
    # hand route has independent commitment. Obelisk is a conflict only when that
    # hand is actually the committed most-played route.
    add(
        "high_card",
        "Obelisk",
    )
    add(
        "pair",
        "Obelisk", "Half Joker", "Supernova", "Card Sharp", "Space Joker",
        "Burnt Joker", "Green Joker", "Burglar", "DNA", "Trading Card", "Hologram",
    )
    add(
        "two_pair",
        "Obelisk", "The Duo", "Jolly Joker", "Sly Joker", "Supernova",
        "Card Sharp", "Space Joker", "Burnt Joker",
    )
    for strategy_id in (
        "three_kind", "straight", "flush", "full_house", "four_kind",
        "straight_flush", "five_kind", "flush_house", "flush_five",
    ):
        add(strategy_id, "Obelisk", "Supernova", "Card Sharp", "Space Joker", "Burnt Joker")
    add("straight", "Fibonacci", "Hack")
    add("flush", "Arrowhead", "Bloodstone", "Onyx Agate", "Rough Gem")
    add("straight_flush", "Arrowhead", "Bloodstone", "Onyx Agate", "Rough Gem", "DNA")
    add("high_card_baron_mime", "Baron", "Mime", "Stuntman")

    # Rank/face relationships with explicit rank/core prerequisites.
    add("aces", "DNA", "Fibonacci", "Odd Todd", "The Idol")
    add("low_rank", "Fibonacci", "Odd Todd", "Even Steven", "Hanging Chad", "Seltzer", "Dusk")
    add("twos", "Hack", "Fibonacci", "Even Steven", "DNA", "Hologram", "The Idol")
    add("ten_four", "Even Steven", "Hack", "DNA", "Hologram", "The Idol")
    add("sixes", "Even Steven", "DNA", "Hologram", "The Idol")
    add("jacks_hit_road", "Faceless Joker", "Mail-In Rebate", "Merry Andy", "Drunkard")
    add("queens_shoot_moon", "Mime", "Reserved Parking")
    add("face_photochad", "Hanging Chad", "Sock and Buskin", "Seltzer", "Dusk")
    add("face_triboulet_sock", "Sock and Buskin", "Hanging Chad", "Seltzer", "Dusk")
    add("face_pareidolia", "Pareidolia")
    add("face_held_economy", "Mime", "Pareidolia")
    add("face_business_card", "Oops! All 6s", "Pareidolia", "Sock and Buskin", "Hanging Chad", "Seltzer", "Dusk")
    add("faceless_ride_bus", "Trading Card", "Faceless Joker", "Hit the Road")
    add("faceless_discard_economy", "Pareidolia", "Merry Andy", "Drunkard", "Hit the Road", "Mail-In Rebate")
    add("idol_exact", "The Idol", "DNA", "Trading Card")

    # Suit/held-card support only counts when the payoff shell exists.
    for strategy_id in ("hearts", "diamonds", "clubs", "spades"):
        add(strategy_id, "Smeared Joker")
    for strategy_id in ("diamonds", "spades"):
        add(strategy_id, "Hanging Chad", "Seltzer", "Dusk", "Sock and Buskin", "Hack")
    add("hearts_bloodstone_oops", "Oops! All 6s")
    add("hearts_bloodstone_retrigger", "Hanging Chad", "Seltzer", "Dusk", "Sock and Buskin", "Hack")
    add("clubs_onyx", "Hanging Chad", "Seltzer", "Dusk", "Sock and Buskin", "Hack")
    add("clubs_seeing_double", "Splash")
    add("blackboard", "Smeared Joker")
    add("raised_fist", "Mime")
    add("ancient_suit_rotation", "Smeared Joker", "Hanging Chad", "Seltzer", "Dusk", "Sock and Buskin", "Hack")
    add("flower_pot_splash", "Splash")
    add("flower_pot_smeared", "Smeared Joker")

    # Enhancement leaves: keep the defining core static, but make shell-dependent
    # partners/support authoritative.
    add("stone_marble_scaling", "Stone Joker", "Hologram", "Driver's License", "Blue Joker", "Certificate")
    add("stone_marble_vampire", "Vampire", "Hologram", "Certificate")
    add("stone_dna_duplication", "DNA", "Hologram", "Stone Joker", "Certificate", "Blue Joker")
    add("stone_high_card", "Half Joker", "Burnt Joker", "Card Sharp", "Supernova", "Blue Joker", "Raised Fist")
    add("glass_breakage", "DNA", "Hologram", "Certificate")
    add("glass_retrigger", "Hanging Chad", "Dusk", "Seltzer", "Sock and Buskin", "Hack", "Splash", "DNA", "Hologram")
    add("steel_density", "DNA", "Hologram", "Certificate", "Blue Joker")
    add("steel_mime", "Mime", "Troubadour", "Juggler", "Raised Fist", "Reserved Parking", "Shoot the Moon")
    add("lucky_cat", "DNA", "Hologram", "Certificate")
    add("lucky_cat_oops", "Oops! All 6s", "Business Card")
    add("lucky_retrigger", "Hanging Chad", "Dusk", "Seltzer", "Sock and Buskin", "Hack", "DNA", "Hologram")
    add("gold_cards_held_mime", "Mime", "Reserved Parking", "To the Moon", "Bull", "Bootstraps", "Rocket", "Cloud 9", "Golden Joker")
    add("gold_cards_ticket", "Hanging Chad", "Dusk", "Seltzer", "Sock and Buskin", "Hack", "Business Card", "Bull", "Bootstraps")
    add("gold_cards_midas", "Pareidolia", "Splash", "Scary Face", "Smiley Face", "Business Card", "Reserved Parking")
    add("gold_cards_midas_ticket", "Midas Mask", "Golden Ticket", "Hanging Chad", "Seltzer", "Dusk", "Sock and Buskin", "Hack", "Business Card", "Bull", "Bootstraps")

    # Every positive Seal relationship is conditional on an actually owned matching
    # Seal, so the entire positive static bucket is authoritative for these leaves.
    for strategy_id in conditional_module._SECTION_FIVE_IDS:
        if strategy_id in RUNTIME_UNIVERSAL_BALATRO_STRATEGIES:
            pairs.setdefault(strategy_id, set()).update(_positive_static_tokens(strategy_id))

    # Destruction/growth/engine pairings.
    add("dagger_sacrifice", "Riff-Raff", "Egg", "Gift Card", "Blueprint", "Brainstorm", "Invisible Joker")
    add("canio_trading", "Trading Card", "Pareidolia", "Faceless Joker", "Merry Andy", "Drunkard")
    add("canio_pareidolia", "Pareidolia", "Trading Card", "Midas Mask", "Splash")
    add("canio_glass", "Glass Joker", "Hanging Chad", "Seltzer", "Dusk", "Sock and Buskin", "Hack", "DNA", "Hologram")
    add("canio_consumable", "Canio")
    add("vampire_midas", "Midas Mask", "Pareidolia", "Splash")
    add("vampire_pareidolia_midas", "Midas Mask", "Pareidolia", "Splash")
    add("madness_solo", "Madness", "Joker Stencil")
    add("madness_eternal", "Madness")
    add("thinning_trading_erosion", "Trading Card", "Erosion")
    add("hologram_dna", "DNA", "Blueprint", "Brainstorm")
    add("hologram_certificate", "Certificate", "Blueprint", "Brainstorm")
    add("hologram_marble", "Marble Joker", "Blueprint", "Brainstorm")
    add("hiker_training", "Hanging Chad", "Seltzer", "Dusk", "Sock and Buskin", "Hack", "Splash", "DNA", "Certificate", "Blueprint", "Brainstorm")
    add("drivers_license", "Midas Mask", "Marble Joker", "Certificate", "DNA", "Hologram", "Blueprint", "Brainstorm")
    add("blue_joker_deck", "Hologram", "Certificate", "Marble Joker", "DNA")

    # Consumable/economy/board/discard support requires the named engine.
    add("vagabond", "Rocket", "To the Moon", "Bull", "Bootstraps", "Cloud 9")
    add("planet_constellation", "Astronomer", "Perkeo", "Satellite")
    add("planet_satellite", "Astronomer", "Perkeo", "Constellation")
    add("planet_constellation_satellite", "Constellation", "Satellite", "Astronomer", "Perkeo")
    add("perkeo_observatory", "Perkeo")
    add("perkeo_cryptid", "Perkeo")
    add("perkeo_tarot_spectral", "Perkeo")
    add("tarot_eight_ball", "Oops! All 6s", "Hanging Chad", "Seltzer", "Dusk", "Fibonacci")
    add("cash_hoard", "Vagabond")
    for strategy_id in ("cash_growth", "cash_bull", "cash_bootstraps", "cash_bull_bootstraps", "cash_cloud_nine"):
        add(strategy_id, "Vagabond")
    add("cash_bull", "Rocket", "To the Moon", "Golden Joker", "Cloud 9", "Golden Ticket")
    add("cash_bootstraps", "Rocket", "To the Moon", "Golden Joker", "Cloud 9", "Golden Ticket")
    add("cash_bull_bootstraps", "Bull", "Bootstraps", "Rocket", "To the Moon")
    add("cash_cloud_nine", "DNA", "Hologram")
    add("campfire", "Gift Card", "Egg", "Riff-Raff", "Cartomancer", "Hallucination", "Perkeo")
    add("flash_card", "Chaos the Clown", "Rocket", "To the Moon")
    add("red_card", "Hallucination", "Fortune Teller")
    add("throwback", "Diet Cola", "Red Card")
    add("joker_stencil", "Invisible Joker", "Riff-Raff")
    add("baseball_card", "Showman")
    add("abstract_joker", "Riff-Raff", "Showman", "Invisible Joker")
    add("swashbuckler", "Egg", "Gift Card", "Riff-Raff", "Invisible Joker")
    for strategy_id in ("discard_castle", "discard_mail_rebate", "discard_yorick"):
        add(strategy_id, "Green Joker", "Banner", "Delayed Gratification", "Ramen", "Burglar", "Merry Andy", "Drunkard")
    add("discard_castle", "Smeared Joker")
    add("discard_mail_rebate", "Trading Card")
    add("discard_yorick", "Certificate")
    for strategy_id in ("no_discard_green", "no_discard_reserve", "no_discard_ramen", "no_discard_burglar"):
        add(strategy_id, "Burglar", "Green Joker", "Banner", "Delayed Gratification", "Ramen", "Trading Card", "Castle", "Mail-In Rebate", "Yorick")
    add("burnt_joker_engine", "Space Joker", "Certificate", "Merry Andy", "Drunkard")
    add("last_hand_acrobat", "Loyalty Card", "Burglar")
    add("last_hand_dusk", "Hanging Chad", "Seltzer", "Splash", "Sock and Buskin", "Hack", "Hiker")
    add("loyalty_cycle", "Burglar", "Acrobat")

    return {key: frozenset(value) for key, value in pairs.items()}


_AUTHORITATIVE_CONDITIONALS = _build_authoritative_pairs()


def install_strategy_conditional_authority_policy() -> None:
    if getattr(conditional_module, "_conditional_authority_policy_installed", False):
        return

    original = conditional_module._is_authoritative_conditional_relationship

    def _is_authoritative_conditional_relationship(strategy_id: str, item: object) -> bool:
        token = conditional_module._item_token(item)
        if token in _AUTHORITATIVE_CONDITIONALS.get(strategy_id, frozenset()):
            return True
        return original(strategy_id, item)

    conditional_module._is_authoritative_conditional_relationship = (
        _is_authoritative_conditional_relationship
    )
    conditional_module._conditional_authority_policy_installed = True
