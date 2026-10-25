# Recognition review and first-frame reuse

Inspected retained failure screenshots from the latest October 25 batch. Thirty-seven recorded frames associated with unavailable Skip/Pon/Kita checks were replayed against the unchanged template bank: thirty-six had no matching target at the sampled locations and one had a unique match. No duplicate-position matching defect was reproduced. Journal image references can precede the exact failure because recording deduplicates frames, so this is not an exact replay of all 474 failed checks.

The longest retained Kita sequence showed Auto Kita enabled, no visible Kita panel, then an own server-confirmed North extraction. The native verifier was reporting a hidden/unavailable client-controlled button, not recognizing a different button incorrectly. Do not increase recognition thresholds or click empty board positions. Revealed opponent hands remain excluded from policy information.

Reduce redundant capture work by allowing the existing assist frame to supply the first gameplay observation for up to 500 ms rather than 250 ms. It must have identical board token and window geometry. The frame is consumed once. Every successful action still requires a distinct newly captured second frame, complete hand/button verification, stable sample comparison and final live board/window checks. Negative frame age, age over 500 ms, changed board and changed geometry reject reuse. This changes the age limit of the first observation, not the confidence thresholds or final-frame requirement.

The previous batch's preflight captures had median duration 0.200 seconds. Each newly eligible reuse avoids one such capture; this is a potential per-action saving, not a measured live improvement or a guarantee for all turns. The recorded logs do not contain ages for rejected cache entries, so the eligible live fraction cannot be established retrospectively.

Failed preflight entries now include the requested action and last observed client-assist states. This will help separate client-managed button disappearance from genuine recognition failures in the next run. Terminal output remains recommended actions only.

Validation covers the 300/500 ms reuse cases, stale/negative ages, mismatched tokens and geometry, and disagreement between reused and fresh observations. No gameplay, mouse action or agent launch was performed. No raw recordings were published. Next: the user-started three-game run should compare capture reuse count, latency distribution and failed-check context.
