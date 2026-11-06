# Ranked rewards Confirm stage

The November 6 recording showed two placement Confirm deliveries followed by a stationary Silver Chest/Bond rewards screen. Both screens matched the generic Match End template at the same button position. They shared a delivery key, exhausting the two-attempt budget before the rewards screen could advance.

Added a separate match_rewards stage using the reviewed Silver Chest heading and Confirm label pixels. Its specific heading overrides the generic Match End match. OCR also distinguishes chest/Bond rewards. Each stage retains at most two deliveries and fresh-frame, state, geometry and eligibility checks. No additional live inputs were sent.

Offline replay classified the recorded placement frame as match_results and the stalled rewards frame as match_rewards, both at (1744, 986). The regression exhausts placement attempts, advances to rewards at the same coordinates, and verifies an independent bounded retry budget. The committed template contains only sampled heading/button pixels, without player or account data. Live advancement remains to be verified in the next user-run match.
