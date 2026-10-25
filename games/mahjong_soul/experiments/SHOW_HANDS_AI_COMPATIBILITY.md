# Show Hands in AI practice rooms

The October 25 attempt stopped producing suggestions because lobby normalization classified `open_hand` as an unsupported special rule. This was an explicit lobby rejection, not a mouse-input failure.

Allow `open_hand` when authenticated mode metadata has `ai` set to true. Keep rejecting the flag in other or unknown room types, and keep every other unsupported special-rule check intact. All registered three/four-player East/South playbooks can use this AI observation setting.

GameState already ignores the opponents' concealed `opens` payload and their revealed draw tile identities. Tests compare otherwise identical hidden-hand and shown-hand events and require identical complete state snapshots and tile counts. No opponent concealed hand is added to policy observations.

Validation: replaying the rejected local lobby through updated normalization selects Three-Player South Attack. Full Mahjong suite: 990 passed, one skipped. No game or agent was launched and no private session payload was committed.

Restart the agent to load the change; Show Hands can remain enabled in the AI room. Live visual delivery with the setting still needs the next user-started run.
