import json
import os
from typing import Dict, Any, Optional

from core.engine.types import Side
from core.engine.constants import HUMAN_SIDE


PROFILES_FILE = "data/profiles.json"


def default_profiles_data() -> Dict[str, Any]:
    return {
        "version": 1,
        "players": [
            {
                "id": "p1",
                "display_name": "Player 1",
                "avatar": {
                    "type": "color",
                    "color": [220, 50, 50],
                    "symbol": "P1",
                },
                "stats": {
                    "overall": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
                    "vs_ai": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
                    "vs_human": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
                },
            },
            {
                "id": "p2",
                "display_name": "Player 2",
                "avatar": {
                    "type": "color",
                    "color": [40, 120, 220],
                    "symbol": "P2",
                },
                "stats": {
                    "overall": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
                    "vs_ai": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
                    "vs_human": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
                },
            },
        ],
        "last_selected": {
            "pvp": {
                "red_player_id": "p1",
                "black_player_id": "p2",
            },
            "ai": {
                "human_player_id": "p1",
            },
        },
    }


def load_profiles() -> Dict[str, Any]:
    if not os.path.exists(PROFILES_FILE):
        data = default_profiles_data()
        save_profiles(data)
        return data
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = default_profiles_data()
        save_profiles(data)
    return data


def save_profiles(data: Dict[str, Any]) -> None:
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def find_player(data: Dict[str, Any], player_id: str) -> Optional[Dict[str, Any]]:
    for p in data.get("players", []):
        if p.get("id") == player_id:
            return p
    return None


def update_stats_for_player(player: Dict[str, Any], result: str, is_vs_ai: bool) -> None:
    stats = player["stats"]

    stats["overall"]["games"] += 1
    if result == "win":
        stats["overall"]["wins"] += 1
    elif result == "loss":
        stats["overall"]["losses"] += 1
    elif result == "draw":
        stats["overall"]["draws"] += 1

    key = "vs_ai" if is_vs_ai else "vs_human"
    stats[key]["games"] += 1
    if result == "win":
        stats[key]["wins"] += 1
    elif result == "loss":
        stats[key]["losses"] += 1
    elif result == "draw":
        stats[key]["draws"] += 1


def apply_game_result_to_profiles(profiles_data: Dict[str, Any],
                                  mode: str,
                                  winner_side: Optional[Side],
                                  is_draw: bool) -> None:
    if mode not in ("pvp", "ai"):
        return

    if mode == "pvp":
        pvp_info = profiles_data.get("last_selected", {}).get("pvp", {})
        red_id = pvp_info.get("red_player_id", "p1")
        black_id = pvp_info.get("black_player_id", "p2")
        red_player = find_player(profiles_data, red_id)
        black_player = find_player(profiles_data, black_id)
        if red_player is None or black_player is None:
            return

        if is_draw or winner_side is None:
            update_stats_for_player(red_player, "draw", is_vs_ai=False)
            update_stats_for_player(black_player, "draw", is_vs_ai=False)
        else:
            if winner_side == Side.RED:
                update_stats_for_player(red_player, "win", is_vs_ai=False)
                update_stats_for_player(black_player, "loss", is_vs_ai=False)
            else:
                update_stats_for_player(red_player, "loss", is_vs_ai=False)
                update_stats_for_player(black_player, "win", is_vs_ai=False)

    elif mode == "ai":
        ai_info = profiles_data.get("last_selected", {}).get("ai", {})
        human_id = ai_info.get("human_player_id", "p1")
        human_player = find_player(profiles_data, human_id)
        if human_player is None:
            return

        if is_draw or winner_side is None:
            update_stats_for_player(human_player, "draw", is_vs_ai=True)
        else:
            if winner_side == HUMAN_SIDE:
                update_stats_for_player(human_player, "win", is_vs_ai=True)
            else:
                update_stats_for_player(human_player, "loss", is_vs_ai=True)

    save_profiles(profiles_data)
