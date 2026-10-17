"""Manual-test strategy cartridge policy; no native input or full risk model."""
from copy import deepcopy
from agents.mahjong_soul.efficiency import EfficiencyPolicy, rank_discards
from games.mahjong_soul.playbook.model import default_mahjong_playbooks
from games.mahjong_soul.playbook.features import discard_features, riichi_threats


class PlaybookPolicy(EfficiencyPolicy):
    def __init__(self, registry=None):
        super().__init__()
        self.registry = default_mahjong_playbooks() if registry is None else registry

    def choose(self, request):
        self.last_analysis = None
        if any(a["kind"] in ("tsumo","ron") for a in request["actions"]):
            return super().choose(request)
        if not any(a["kind"] == "discard" for a in request["actions"]):
            return super().choose(request)
        board = request["observation"]["board"]
        book = self.registry.for_observation(request["observation"])
        value = book.thresholds_for("D1"); defense = book.thresholds_for("D2"); riichi = book.thresholds_for("D3")
        ranked = rank_discards(request); threats = riichi_threats(board)
        for option in ranked:
            option.update(discard_features(board,option["action"]["tile"]))
            option["value_loss"] = (option["dora_loss"]*value["dora_loss_weight"]
                                    + option["yakuhai_pair_loss"]*value["yakuhai_pair_loss_weight"]
                                    + option["yakuhai_triplet_loss"]*value["yakuhai_triplet_loss_weight"])
        # Fold only on positive genbutsu evidence: no speculative risk probabilities.
        fold = bool(threats and ranked[0]["shanten"] >= defense["fold_from_shanten"]
                    and any(o["safe_against_riichi_seats"] for o in ranked))
        def key(option):
            safe = len(option["safe_against_riichi_seats"])
            base = (option["shanten"],-option["ukeire"])
            tail = (option["value_loss"],option["action"]["tile"].startswith("0"),
                    option["action"]["tile"] != board["self"].get("drawn_tile"),option["action"]["tile"])
            return (-safe,)+base+tail if fold else base+(-safe,)+tail
        ranked.sort(key=key)
        best = ranked[0]; chosen = best["action"]
        offered = {a["tile"]:a for a in request["actions"] if a["kind"] == "riichi"}
        if offered and riichi["enabled"] and (not threats or riichi["allow_under_riichi_threat"]) and not fold:
            eligible = [o for o in ranked if o["action"]["tile"] in offered and o["shanten"] == 0]
            if not eligible: raise ValueError("Riichi has no tenpai candidate")
            best = eligible[0]; chosen = offered[best["action"]["tile"]]
        self.last_analysis = {"board_token":request["board_token"],"playbook":book.name,
                              "playbook_version":book.version,"mode":"fold" if fold else "efficiency",
                              "shanten":best["shanten"],"ukeire":best["ukeire"],
                              "value_loss":best["value_loss"],"yakuhai_triplets":best["yakuhai_triplets"],
                              "riichi_threat_seats":[p["seat"] for p in threats],
                              "safe_against_riichi_seats":best["safe_against_riichi_seats"],
                              "improving_tiles":deepcopy(best["improving_tiles"])}
        return deepcopy(chosen)
