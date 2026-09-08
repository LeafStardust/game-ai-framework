from __future__ import annotations

"""SHOP runtime boundary registration for Red/White production.

The former implementation patched the deleted ``build_health_policy`` compatibility
layer to mark hypothetical Build Health states and disable a legacy named bundle
planner. Both authorities are gone. The remaining runtime contract is therefore
only an idempotent registration marker used by the SHOP expectation stack.
"""

from games.balatro.shop_arbiter import BuildAwareShopArbiter


def install_shop_runtime_contract_policy() -> None:
    """Record that the legacy SHOP compatibility authority is retired."""
    if getattr(BuildAwareShopArbiter, "_rw_runtime_contract_installed", False):
        return
    BuildAwareShopArbiter._rw_runtime_contract_installed = True
