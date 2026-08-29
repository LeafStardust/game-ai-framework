"""Production Balatro live runtime.

This package owns autonomous orchestration and read-only live-state acquisition.
Gameplay mutations are executed by :mod:`games.balatro.live.injected`.
"""

from .round_eval_checkout_fastpath import install_round_eval_checkout_fastpath


install_round_eval_checkout_fastpath()
