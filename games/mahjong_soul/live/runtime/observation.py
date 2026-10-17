"""Package reader snapshots for consumers without choosing or sending actions."""

from copy import deepcopy

from games.mahjong_soul.live.runtime.input import board_token


def observation_from_snapshot(report):
    """Return an independent, versioned observation using absolute seat indices.

    Available operations retain the server payload. They are not expanded into
    executable actions: timing, combinations and unknown codes stay intact.
    """
    state = report.get("state")
    observation = {
        "version": 1,
        "ready": bool(report.get("state_ready")),
        "source": {"connection": report.get("game_connection"),
                   "generation": report.get("game_generation", 0),
                   "board_token": board_token(report),
                   "connection_open": bool(report.get("connection_open")),
                   "step": state.get("step") if state else None,
                   "last_event": deepcopy(report.get("last_event"))},
        "status": state.get("status") if state else "waiting_for_game",
        "issues": list(state.get("issues", [])) if state else [],
        "board": None,
    }
    if state is None:
        observation["ready"] = False
        return observation
    seat = state["seat"]
    players = []
    for index in range(state["player_count"]):
        players.append({"seat": index, "is_self": index == seat,
                        "score": state["scores"][index] if index < len(state["scores"]) else None,
                        "discards": deepcopy(state["discards"][index]),
                        "melds": deepcopy(state["melds"][index]),
                        "norths": state["norths"][index],
                        "riichi": state["riichi"][index]})
    observation["board"] = {
        "player_count": state["player_count"], "self_seat": seat,
        "self": {"hand": list(state["hand"]), "drawn_tile": state["drawn_tile"],
                 "furiten": deepcopy(state["furiten"])},
        "players": players, "round": deepcopy(state["round"]),
        "last_actor": state["turn"], "wall_remaining": state["left_tile_count"],
        "dora_indicators": list(state["doras"]),
        "visible_tile_counts": dict(state["visible_tile_counts"]),
        "visibility_complete": state["visibility_complete"],
        "available_operations": deepcopy(state["operations"]),
    }
    return observation
