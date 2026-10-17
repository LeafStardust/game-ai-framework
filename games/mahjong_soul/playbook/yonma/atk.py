"""Four-player attack settings for manual shadow testing."""
from games.mahjong_soul.playbook.model import MahjongPlaybook


def attack_playbook():
    return MahjongPlaybook(4,"yonma-manual-atk",style="atk",version="0.2",strategy={
        "discard_value":{"dora_loss_weight":2.0,"yakuhai_pair_loss_weight":1.25,
                         "yakuhai_triplet_loss_weight":4.0,"max_ukeire_sacrifice":6,
                         "ukeire_per_value":2.0,"pair_break_weight":2.0,"points_per_ukeire":2000,"potential_weight":.75},
        "defense":{"push_value_floor":3,"push_max_shanten":2,
                   "push_min_wall":12,"push_max_danger":75,
                   "distant_push_han":4,"distant_push_ukeire":20,"distant_push_wall":24},
        "riichi":{"enabled":True,"allow_under_riichi_threat":True,"minimum_ukeire":2,
                  "minimum_ukeire_under_threat":6,"max_threats":1,"minimum_wall":8,
                  "allow_furiten":False,"dama_min_points":7700,"dama_min_waits":4,"dama_gain_ratio":1.25},
        "calls":{"max_shanten":1,"minimum_han":2,"cheap_tenpai_waits":3,
                 "kan_min_wall":16,"kan_min_han":4,"kan_ukeire_loss":2}})
