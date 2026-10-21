"""Three-Player South Attack: value first, then winning speed and safety."""
from dataclasses import replace
from games.mahjong_soul.playbook.yonma.south_attack import south_attack_playbook


def three_player_south_attack_playbook():
    # A fresh source book keeps each format's mutable settings independent.
    base=south_attack_playbook()
    settings=base.strategy
    settings["riichi"]["max_threats"]=2
    return replace(base,player_count=3,name="Three-Player South Attack",
                   version="0.1",strategy=settings)
