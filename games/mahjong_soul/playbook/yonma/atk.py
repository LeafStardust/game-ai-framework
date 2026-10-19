"""4 Player South Wind ATK: high-value, always-push settings."""
from games.mahjong_soul.playbook.model import MahjongPlaybook


def attack_playbook():
    return MahjongPlaybook(4,"4 Player South Wind ATK",style="atk",version="0.8",strategy={
        "discard_value":{"dora_loss_weight":2.0,"yakuhai_pair_loss_weight":1.25,
                         "yakuhai_triplet_loss_weight":4.0,"max_ukeire_sacrifice":14,
                         "ukeire_per_value":2.0,"pair_break_weight":2.0,"points_per_ukeire":2000,"potential_weight":.75,
                         "minimum_ukeire_fraction":.7,"allow_value_rebuild":False,"han_weight":20,"shanten_cost":18,"route_cost_weight":4,
                         "ukeire_weight":2.5,"value_rebuild_han_gain":2,"value_rebuild_min_wall":24},
        "defense":{"always_push":True,"push_value_floor":3,"push_max_shanten":2,
                   "push_min_wall":12,"push_max_danger":75,
                   "distant_push_han":4,"distant_push_ukeire":20,"distant_push_wall":24},
        "riichi":{"enabled":True,"allow_under_riichi_threat":True,"minimum_ukeire":1,
                  "minimum_ukeire_under_threat":1,"max_threats":3,"minimum_wall":4,
                  "allow_furiten":False,"dama_min_points":0,"dama_min_waits":1,"dama_gain_ratio":1.0},
        "calls":{"minimum_ukeire_fraction":.7,"max_shanten":3,"minimum_han":3,"max_route_cost":4,
                 "allow_value_calls":True,"avoid_kan_under_threat":False,"cheap_tenpai_waits":3,"allow_cheap_tenpai":False,
                 "kan_min_wall":8,"kan_min_han":3,"kan_ukeire_loss":2}})
