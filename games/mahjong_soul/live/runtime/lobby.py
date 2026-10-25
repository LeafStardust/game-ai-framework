"""Normalize authenticated match format; never infer length from current Wind."""
from copy import deepcopy

SPECIAL_RULES=("guyi_mode","dora3_mode","begin_open_mode","jiuchao_mode","muyu_mode",
 "open_hand","xuezhandaodi","huansanzhang","chuanma","reveal_discard","field_spell_mode",
 "zhanxing","tianming_mode","enable_shiti","enable_renhe","yongchang_mode","hunzhiyiji_mode",
 "wanxiangxiuluo_mode","beishuizhizhan_mode","disable_double_yakuman","disable_composite_yakuman",
 "disable_leijiyiman","disable_multi_yukaman","have_qieshangmanguan","disable_double_wind_four_fu")


def detect_lobby(data):
    config=data.get("game_config") or {};mode=config.get("mode") or {}
    seats=data.get("seat_list") or [];count=len(seats) if len(seats) in (3,4) else None
    code=mode.get("mode");length={(4,1):"east",(4,2):"south",(3,11):"east",(3,12):"south"}.get((count,code)) if type(code) is int else None
    detail=deepcopy(mode.get("detail_rule") or {})
    # Show Hands is an observation aid in AI practice rooms, not a scoring
    # variant. Opponent concealed tiles remain excluded by GameState.
    unsupported=[key for key in SPECIAL_RULES if detail.get(key)
                 and not (key=="open_hand" and mode.get("ai") is True)]
    if detail.get("fanfu",1) not in (0,1):unsupported.append("fanfu")
    known=count is not None and length is not None
    return {"source":"authGame","identified":known,"player_count":count,"match_length":length,
            "mode_code":code,"category":config.get("category"),"ai":mode.get("ai"),
            "room_id":(config.get("meta") or {}).get("room_id"),
            "rule_details":detail,"unsupported_rules":unsupported,
            "label":f"{count} Player {length.title()} Wind" if known else "Unknown lobby"}


def unknown_lobby():
    return {"source":None,"identified":False,"player_count":None,"match_length":None,
            "unsupported_rules":[],"label":"Unknown lobby"}
