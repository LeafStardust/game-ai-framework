"""Connection-scoped input eligibility for authenticated AI and ranked games."""


def input_game_verified(owner,report):
    if not getattr(owner,"require_ai",False):return True
    key=(report.get("game_connection"),report.get("game_generation",0))
    if key in owner.ai_games:return True
    if not getattr(owner,"allow_ranked",False) or key not in getattr(owner,"ranked_games",set()):return False
    lobby=(report.get("state") or {}).get("lobby") or {}
    return (lobby.get("ranked") is True and lobby.get("identified") is True
            and not lobby.get("unsupported_rules"))
