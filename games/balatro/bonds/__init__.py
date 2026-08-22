from games.balatro.bonds.burnt import (
    BURNT_RANK_POLICIES,
    BURNT_RANK_THRESHOLDS,
    BurntBondContext,
    evaluate_burnt_bond,
)
from games.balatro.bonds.catalogue_batch_one import *
from games.balatro.bonds.catalogue_batch_two import *
from games.balatro.bonds.catalogue_batch_three import *
from games.balatro.bonds.catalogue_batch_four import *
from games.balatro.bonds.catalogue_batch_five import *
from games.balatro.bonds.held_cards import (
    HELD_CARDS_RANK_POLICIES,
    HELD_CARDS_RANK_THRESHOLDS,
    evaluate_held_cards_bond,
)
from games.balatro.bonds.no_face_cards import (
    NO_FACE_CARDS_BOND_ID,
    NO_FACE_CARDS_RANK_POLICIES,
    NO_FACE_CARDS_RANK_THRESHOLDS,
    NO_FACE_CARDS_RELATIONSHIPS,
    evaluate_no_face_cards_bond,
)
from games.balatro.bonds.vampire import (
    VAMPIRE_BOND_ID,
    VAMPIRE_POLICIES,
    VAMPIRE_RELATIONSHIPS,
    VAMPIRE_THRESHOLDS,
    evaluate_vampire_bond,
)
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization, MechanicalRole
from games.balatro.bonds.mechanical_roles import ROLE_REGISTRY, enrich_contribution, enrich_contributions, enrich_development
from games.balatro.bonds.authority_calibration import apply_rank_authority_audit

apply_rank_authority_audit()

from games.balatro.bonds.joker_coverage_extensions import apply_joker_coverage_extensions
apply_joker_coverage_extensions()

# Refresh public exports after calibration and post-freeze coverage extensions.
from games.balatro.bonds.catalogue_batch_one import *
from games.balatro.bonds.catalogue_batch_two import *
from games.balatro.bonds.catalogue_batch_three import *
from games.balatro.bonds.catalogue_batch_four import *
from games.balatro.bonds.catalogue_batch_five import *
from games.balatro.bonds.held_cards import HELD_CARDS_RANK_POLICIES, HELD_CARDS_RANK_THRESHOLDS, evaluate_held_cards_bond
from games.balatro.bonds.no_face_cards import (
    NO_FACE_CARDS_BOND_ID,
    NO_FACE_CARDS_RANK_POLICIES,
    NO_FACE_CARDS_RANK_THRESHOLDS,
    NO_FACE_CARDS_RELATIONSHIPS,
    evaluate_no_face_cards_bond,
)
from games.balatro.bonds.vampire import (
    VAMPIRE_BOND_ID,
    VAMPIRE_POLICIES,
    VAMPIRE_RELATIONSHIPS,
    VAMPIRE_THRESHOLDS,
    evaluate_vampire_bond,
)
from games.balatro.bonds.realization_held import (
    HELD_REALIZERS,
    realize_held_cards,
    realize_held_family,
    realize_held_retrigger,
    realize_kings,
    realize_queens,
    realize_steel,
)

__all__ = [name for name in globals() if name.isupper() or name.startswith("evaluate_") or name.startswith("enrich_") or name.startswith("realize_") or name in {
    "BondContribution", "BondDevelopment", "BondRank", "BondRealization", "MechanicalRole", "BurntBondContext"
}]
