"""Three-player East: immediate winning progress, then defense and value."""
from dataclasses import replace
from games.mahjong_soul.playbook.yonma.east_speed import east_speed_playbook


def three_player_east_speed_playbook():
    base=east_speed_playbook();settings=base.strategy
    # Zero loss of improving copies; never rebuild for value. More permissive
    # productive Pon/ready-hand pushes than the four-player East policy.
    settings["discard_value"].update(riichi_speed_first=True)
    settings["calls"].update(max_shanten=4,max_route_cost=4)
    settings["riichi"].update(minimum_ukeire=1,minimum_ukeire_under_threat=2,minimum_wall=4,
                              dama_gain_ratio=1.0)
    settings["defense"].update(push_min_wall=6,push_max_danger=85)
    return replace(base,player_count=3,name="Three-Player East Speed",version="0.1",strategy=settings)
