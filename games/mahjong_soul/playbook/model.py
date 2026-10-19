"""Versioned strategy settings; game rules and feature extraction live elsewhere."""
from copy import deepcopy
from dataclasses import dataclass, field

class UnsupportedLobby(ValueError):
    """No compatible playbook; do not issue a fallback action."""


LAYERS = {"D1":"discard_value", "D2":"defense", "D3":"riichi"}


@dataclass(frozen=True)
class MahjongPlaybook:
    player_count: int
    name: str
    version: str = "0.1"
    strategy: dict = field(default_factory=dict)
    style: str = "balanced"
    match_length: str | None = None

    def thresholds_for(self, layer):
        if str(layer).upper() not in LAYERS: raise ValueError("Unknown Mahjong decision layer")
        value = self.strategy.get(LAYERS[str(layer).upper()], {})
        if not isinstance(value, dict): raise TypeError("Threshold block must be a mapping")
        return deepcopy(value)


class MahjongPlaybookRegistry:
    def __init__(self): self._books = {}
    def register(self, playbook):
        if playbook.player_count not in (3,4): raise ValueError("Unsupported player count")
        key = (playbook.player_count, playbook.style, playbook.match_length)
        if key in self._books: raise ValueError("Duplicate Mahjong playbook")
        self._books[key] = playbook
    def get(self, player_count, style="balanced", match_length=None):
        # Explicit legacy/offline access retains the historical ATK default.
        if match_length is None and style=="atk":match_length="south"
        try:
            return self._books.get((player_count,style,match_length)) or self._books[(player_count,style,None)]
        except KeyError as error: raise LookupError("No playbook for player count and style") from error
    def for_observation(self, observation, style="balanced"):
        board=observation["board"]
        # Old snapshots predate lobby capture. Live readers always supply this
        # field, including an explicit unknown value until authentication.
        if "lobby" not in board:return self.get(board["player_count"],style)
        lobby=board["lobby"]
        if not lobby.get("identified"):raise UnsupportedLobby("Lobby format is unknown; capture game authentication first")
        if lobby.get("player_count")!=board["player_count"]:raise UnsupportedLobby("Lobby player count disagrees with board")
        if lobby.get("unsupported_rules"):raise UnsupportedLobby("Unsupported lobby rules: "+", ".join(lobby["unsupported_rules"]))
        try:return self.get(board["player_count"],style,lobby["match_length"])
        except LookupError as error:
            raise UnsupportedLobby(f"No {style.upper()} playbook for {lobby['label']}") from error


def default_mahjong_playbooks():
    registry = MahjongPlaybookRegistry()
    for count, name in [(3,"sanma-manual-balanced"),(4,"yonma-manual-balanced")]:
        registry.register(MahjongPlaybook(count,name,strategy={
            "discard_value":{"dora_loss_weight":1.0,"yakuhai_pair_loss_weight":.5,"yakuhai_triplet_loss_weight":2.0},
            "defense":{"fold_from_shanten":2},
            "riichi":{"enabled":True,"allow_under_riichi_threat":False}}))
    from games.mahjong_soul.playbook.yonma.atk import attack_playbook
    registry.register(attack_playbook())
    from games.mahjong_soul.playbook.yonma.east import east_playbook
    registry.register(east_playbook())
    return registry
