"""Manual-test strategy cartridge policy; no native input or full risk model."""
from copy import deepcopy
from agents.mahjong_soul.efficiency import EfficiencyPolicy, rank_discards
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from games.mahjong_soul.playbook.features import discard_features, riichi_threats


class PlaybookPolicy(EfficiencyPolicy):
    def __init__(self, registry=None, *, style="balanced"):
        super().__init__()
        self.style = style
        self.registry = default_mahjong_playbooks() if registry is None else registry

    def choose(self, request):
        self.last_analysis = None
        board = request["observation"]["board"]
        book = self.registry.for_observation(request["observation"], self.style)
        if any(a["kind"] in ("tsumo","ron") for a in request["actions"]):
            return super().choose(request)
        if not any(a["kind"] == "discard" for a in request["actions"]):
            return super().choose(request)
        value = book.thresholds_for("D1"); defense = book.thresholds_for("D2"); riichi = book.thresholds_for("D3")
        ranked = rank_discards(request); threats = riichi_threats(board)
        for option in ranked:
            option.update(discard_features(board,option["action"]["tile"]))
            option["value_loss"] = (option["dora_loss"]*value["dora_loss_weight"]
                                    + option["yakuhai_pair_loss"]*value["yakuhai_pair_loss_weight"]
                                    + option["yakuhai_triplet_loss"]*value["yakuhai_triplet_loss_weight"])
        best_shanten = ranked[0]["shanten"]
        best_ukeire = max(o["ukeire"] for o in ranked if o["shanten"] == best_shanten)
        allowance = value.get("max_ukeire_sacrifice",0)
        attack_candidates = [o for o in ranked if o["shanten"] == best_shanten
                             and o["ukeire"] >= best_ukeire-allowance]
        def offense_key(option):
            safe = len(option["safe_against_riichi_seats"])
            return (option["shanten"],-option["ukeire"]+option["value_loss"]*value.get("ukeire_per_value",0),
                    -safe, option["value_loss"],option["action"]["tile"].startswith("0"),
                    option["action"]["tile"] != board["self"].get("drawn_tile"),option["action"]["tile"])
        attack_candidates.sort(key=offense_key)
        attacking = attack_candidates[0]
        attack_value = attacking["retained_bonus"]+attacking["yakuhai_units"]
        wall = board.get("wall_remaining")
        push = bool(threats and len(threats) == 1 and "push_value_floor" in defense
                    and best_shanten <= defense["push_max_shanten"]
                    and attack_value >= defense["push_value_floor"]
                    and (not attacking["has_open_meld"] or attacking["yakuhai_units"] > 0)
                    and type(wall) is int and wall >= defense["push_min_wall"])
        fold_distance = (defense.get("multiple_threat_fold_from_shanten",defense["fold_from_shanten"])
                         if len(threats) >= 2 else defense["fold_from_shanten"])
        fold = bool(threats and best_shanten >= fold_distance and not push
                    and any(o["safe_against_riichi_seats"] for o in ranked))
        if fold:
            ranked.sort(key=lambda o:(-len(o["safe_against_riichi_seats"]),o["shanten"],-o["ukeire"],
                                       o["value_loss"],o["action"]["tile"].startswith("0"),
                                       o["action"]["tile"] != board["self"].get("drawn_tile"),o["action"]["tile"]))
            best = ranked[0]
        else:
            best = attacking
        chosen = best["action"]
        offered = {a["tile"]:a for a in request["actions"] if a["kind"] == "riichi"}
        allow_riichi = (riichi["enabled"] and not fold
                         and (not threats or riichi["allow_under_riichi_threat"])
                         and len(threats) <= riichi.get("max_threats",99)
                         and (riichi.get("allow_furiten",True) or board["self"].get("furiten") is False)
                         and ("minimum_wall" not in riichi or type(wall) is int and wall >= riichi["minimum_wall"]))
        if offered and allow_riichi:
            minimum = riichi.get("minimum_ukeire_under_threat",0) if threats else riichi.get("minimum_ukeire",0)
            eligible = [o for o in ranked if o["action"]["tile"] in offered
                        and o["shanten"] == 0 and o["ukeire"] >= minimum]
            if eligible:
                max_waits = max(o["ukeire"] for o in eligible)
                eligible = [o for o in eligible if o["ukeire"] >= max_waits-allowance]
                best = min(eligible,key=offense_key); chosen = offered[best["action"]["tile"]]
        self.last_analysis = {"board_token":request["board_token"],"playbook":book.name,
                              "playbook_version":book.version,"style":book.style,
                              "mode":"fold" if fold else "attack_push" if push else "efficiency",
                              "shanten":best["shanten"],"ukeire":best["ukeire"],
                              "retained_value_proxy":best["retained_bonus"]+best["yakuhai_units"],
                              "value_loss":best["value_loss"],"yakuhai_triplets":best["yakuhai_triplets"],
                              "riichi_threat_seats":[p["seat"] for p in threats],
                              "safe_against_riichi_seats":best["safe_against_riichi_seats"],
                              "improving_tiles":deepcopy(best["improving_tiles"])}
        return deepcopy(chosen)
