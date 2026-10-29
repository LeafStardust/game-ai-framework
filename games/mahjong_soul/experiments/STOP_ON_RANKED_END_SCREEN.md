# Stop at the ranked end screen

Previously the worker exited as soon as the server marked the Xth match ended, before the final visual results and One More Game screen appeared. Defer ranked shutdown until that end screen is actually verified.

When the match budget is exhausted, clear pending gameplay proposals and admit no further gameplay/assist preparation. Continue the existing captured-result navigation through required Continue/Confirm screens. On the final authenticated ranked One More Game screen, require result context, the unique button label, matching source/current pixels, an independent fresh matching capture, unchanged board/window and the already-completed run identity. Record final_result_screen_verified and finish the worker. Do not click One More Game at the limit.

Below the limit, requeue behavior remains unchanged. With X=3, requeue after the first two matches; after the third, finish the visual result sequence and stop on the button screen. Unlimited runs have no budget-triggered final stop. Existing custom AI-room budget behavior is unchanged; this adjustment concerns the ranked end-screen sequence requested by the user.

Regression coverage exercises the real follower limit logic: a completed one-match ranked run remains enabled for a required Confirm, then reaches a verified One More Game screen and exits with no extra queue click. Separate tests cover X=1/X=3, two intermediate requeues, budget changes during verification, stable/unstable screens and no further input after finishing.

The game was closed during read-only window inspection, so the actual live final layout remains unvalidated. The change is implemented and tested with synthetic/fake-mouse screens. No game, agent or ranked queue was launched, and no real UI input was sent.

Validation: full Mahjong suite passed 1,067 tests with one skipped.
