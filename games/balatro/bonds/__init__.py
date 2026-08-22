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
from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.authority_calibration import apply_rank_authority_audit

# Catalogue Audit Pass 3: evaluator modules own identity/contributions; this layer
# calibrates only rank geometry and high-end persistent-state authority.
apply_rank_authority_audit()

# Some implementation-pass threshold constants alias shared dictionaries. Audit
# Pass 3 intentionally rebinds selected module constants, so refresh public
# package exports after calibration to prevent stale pre-audit tables.
from games.balatro.bonds.catalogue_batch_one import *
from games.balatro.bonds.catalogue_batch_two import *
from games.balatro.bonds.catalogue_batch_three import *
from games.balatro.bonds.catalogue_batch_four import *
from games.balatro.bonds.catalogue_batch_five import *
from games.balatro.bonds.held_cards import HELD_CARDS_RANK_POLICIES, HELD_CARDS_RANK_THRESHOLDS, evaluate_held_cards_bond

__all__ = [name for name in globals() if name.isupper() or name.startswith("evaluate_") or name in {
    "BondContribution", "BondDevelopment", "BondRank", "BondRealization", "BurntBondContext"
}]
