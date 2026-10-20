"""Four-player East: speed, then defense, then hand value."""
from dataclasses import replace
from games.mahjong_soul.playbook.yonma.south_attack import south_attack_playbook


def east_speed_playbook():
    base=south_attack_playbook()
    # Each call constructs independent settings; South is never mutated.
    settings=base.strategy
    settings["discard_value"].update(speed_first=True,max_ukeire_sacrifice=0,minimum_ukeire_fraction=1,
                                      han_weight=1,route_cost_weight=0,allow_value_rebuild=False)
    settings["defense"].update(always_push=False,push_max_shanten=1,push_value_floor=1,
                               push_min_wall=8,push_max_danger=75)
    settings["riichi"].update(minimum_ukeire=2,minimum_ukeire_under_threat=4,max_threats=1,
                              minimum_wall=8,dama_min_points=5200,dama_gain_ratio=1.25)
    settings["calls"].update(minimum_han=1,minimum_ukeire_fraction=1,max_shanten=3,
                             allow_cheap_tenpai=True,cheap_tenpai_waits=1,
                             avoid_kan_under_threat=True,kan_min_wall=16,kan_min_han=1,kan_ukeire_loss=0)
    return replace(base,name="Four-Player East Speed",match_length="east",version="0.2",strategy=settings)
