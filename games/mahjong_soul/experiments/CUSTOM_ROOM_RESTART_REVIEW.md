# Latest South match and custom-room restart

Session `20261023T120618-056450Z`, revision `d05af1c6`: first place, 52,300
points, opponents 19,800 and 32,900. Two Ron wins (four and six Han), no deal-ins.
One hand ended in a draw; seven had wins. This single result does not establish
a measured policy win-rate improvement.

There were 99 submitted actions and 98 server confirmations. One planned 1 Pin
discard was not confirmed; later a different own 9 Sou discard arrived. The
controller blocked that attempt and recovered at the next verified board.
The recording does not establish whether the unmatched discard resulted from
lost input, client timeout or user input. Do not count it as successful delivery.

Recommendation-to-submit median was 1.340 seconds, maximum 4.444. Sixty-four of
99 met 1.5 seconds; thirty-five did not. Capture timing median was 179 ms and
maximum 264 ms over 1,650 frames; recording median was under 0.01 ms and maximum
9.3 ms. Screenshot acquisition/encoding dominates disk recording overhead here.
All twenty assist changes were confirmed. Sixteen result Confirm clicks were
delivered with seven explicit game-state-advanced confirmations.

The final recording includes the custom room screen. Its real OCR and cropped
pixels now cover restart recognition, enabled Start, roster stability, room
identity, format, completed-match/AI verification and once-per-match delivery.
Restart is automatic in the existing agent package after final Confirm returns
to the same custom AI room. It does not launch the app or create/join rooms.
The first real Start delivery remains to be validated in a user-started session.
No game or agent was launched during this work.
