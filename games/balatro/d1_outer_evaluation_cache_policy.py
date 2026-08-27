from __future__ import annotations

"""Compatibility shim for the retired outer D1 cache installer.

Outer-state action/projection/guaranteed-clear memoization now lives directly in
``LiveHandDecisionEvaluator``.  Keep this no-op entry point temporarily because the
package registration file still imports it; it must not wrap canonical methods a
second time.
"""


def install_d1_outer_evaluation_cache_policy() -> None:
    return
