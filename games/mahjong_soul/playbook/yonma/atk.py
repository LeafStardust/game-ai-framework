"""Four-player attack settings for manual shadow testing."""
from games.mahjong_soul.playbook.model import MahjongPlaybook


def attack_playbook():
    return MahjongPlaybook(4,"yonma-manual-atk",style="atk",strategy={
        "discard_value":{"dora_loss_weight":2.0,"yakuhai_pair_loss_weight":1.25,
                         "yakuhai_triplet_loss_weight":4.0,"max_ukeire_sacrifice":6,
                         "ukeire_per_value":2.0},
        "defense":{"fold_from_shanten":2,"push_value_floor":3,"push_max_shanten":2,
                   "push_min_wall":12,"multiple_threat_fold_from_shanten":2},
        "riichi":{"enabled":True,"allow_under_riichi_threat":True,"minimum_ukeire":2,
                  "minimum_ukeire_under_threat":6,"max_threats":1,"minimum_wall":8,
                  "allow_furiten":False}})
