"""Versioned strategy settings; game rules and feature extraction live elsewhere."""
from copy import deepcopy
from dataclasses import dataclass, field

LAYERS = {"D1":"discard_value", "D2":"defense", "D3":"riichi"}


@dataclass(frozen=True)
class MahjongPlaybook:
    player_count: int
    name: str
    version: str = "0.1"
    strategy: dict = field(default_factory=dict)

    def thresholds_for(self, layer):
        if str(layer).upper() not in LAYERS: raise ValueError("Unknown Mahjong decision layer")
        value = self.strategy.get(LAYERS[str(layer).upper()], {})
        if not isinstance(value, dict): raise TypeError("Threshold block must be a mapping")
        return deepcopy(value)


class MahjongPlaybookRegistry:
    def __init__(self): self._books = {}
    def register(self, playbook):
        if playbook.player_count not in (3,4): raise ValueError("Unsupported player count")
        if playbook.player_count in self._books: raise ValueError("Duplicate Mahjong playbook")
        self._books[playbook.player_count] = playbook
    def get(self, player_count):
        try: return self._books[player_count]
        except KeyError as error: raise LookupError("No playbook for player count") from error
    def for_observation(self, observation):
        return self.get(observation["board"]["player_count"])


def default_mahjong_playbooks():
    registry = MahjongPlaybookRegistry()
    for count, name in [(3,"sanma-manual-balanced"),(4,"yonma-manual-balanced")]:
        registry.register(MahjongPlaybook(count,name,strategy={
            "discard_value":{"dora_loss_weight":1.0,"yakuhai_pair_loss_weight":.5,"yakuhai_triplet_loss_weight":2.0},
            "defense":{"fold_from_shanten":2},
            "riichi":{"enabled":True,"allow_under_riichi_threat":False}}))
    return registry
