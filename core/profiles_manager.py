import json
import os
from typing import Dict, Any, Optional

from core.engine.ai_engine import AI_LEVELS
from core.engine.constants import HUMAN_SIDE
from core.engine.types import Side


PROFILES_FILE = "data/profiles.json"
PROFILE_VERSION = 2
DEFAULT_ELO = 1200
ELO_K_FACTOR = 32


def default_stats_block() -> Dict[str, Dict[str, int]]:
    return {
        "overall": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
        "vs_ai": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
        "vs_human": {"games": 0, "wins": 0, "losses": 0, "draws": 0},
    }


def default_profiles_data() -> Dict[str, Any]:
    return {
        "version": PROFILE_VERSION,
        "players": [
            {
                "id": "p1",
                "display_name": "Player 1",
                "avatar": {
                    "type": "color",
                    "color": [220, 50, 50],
                    "symbol": "P1",
                },
                "elo": DEFAULT_ELO,
                "stats": default_stats_block(),
            },
            {
                "id": "p2",
                "display_name": "Player 2",
                "avatar": {
                    "type": "color",
                    "color": [40, 120, 220],
                    "symbol": "P2",
                },
                "elo": DEFAULT_ELO,
                "stats": default_stats_block(),
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


def ensure_stats_structure(stats: Dict[str, Any]) -> bool:
    changed = False
    for key in ("overall", "vs_ai", "vs_human"):
        if key not in stats or not isinstance(stats[key], dict):
            stats[key] = {"games": 0, "wins": 0, "losses": 0, "draws": 0}
            changed = True
        else:
            block = stats[key]
            for field in ("games", "wins", "losses", "draws"):
                if field not in block:
                    block[field] = 0
                    changed = True
    return changed


def ensure_player_defaults(player: Dict[str, Any]) -> bool:
    changed = False
    if "stats" not in player or not isinstance(player["stats"], dict):
        player["stats"] = default_stats_block()
        changed = True
    else:
        if ensure_stats_structure(player["stats"]):
            changed = True

    if "elo" not in player:
        player["elo"] = DEFAULT_ELO
        changed = True
    return changed


def ensure_profiles_schema(data: Dict[str, Any]) -> bool:
    changed = False
    if data.get("version") != PROFILE_VERSION:
        data["version"] = PROFILE_VERSION
        changed = True

    players = data.get("players")
    if not isinstance(players, list):
        data["players"] = default_profiles_data()["players"]
        players = data["players"]
        changed = True

    for player in players:
        if ensure_player_defaults(player):
            changed = True

    last_sel = data.get("last_selected")
    if not isinstance(last_sel, dict):
        data["last_selected"] = default_profiles_data()["last_selected"]
        changed = True
    else:
        if "pvp" not in last_sel:
            last_sel["pvp"] = {"red_player_id": "p1", "black_player_id": "p2"}
            changed = True
        if "ai" not in last_sel:
            last_sel["ai"] = {"human_player_id": "p1"}
            changed = True

    return changed


def expected_score(rating: float, opponent_rating: float) -> float:
    return 1.0 / (1 + 10 ** ((opponent_rating - rating) / 400))


def get_player_elo(player: Dict[str, Any]) -> float:
    try:
        return float(player.get("elo", DEFAULT_ELO))
    except Exception:
        return float(DEFAULT_ELO)


def update_player_elo(player: Dict[str, Any], opponent_rating: float, result: str) -> None:
    rating = get_player_elo(player)
    actual_score = {"win": 1.0, "loss": 0.0, "draw": 0.5}.get(result, 0.5)
    expected = expected_score(rating, opponent_rating)
    new_rating = rating + ELO_K_FACTOR * (actual_score - expected)
    player["elo"] = int(round(new_rating))


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

    changed = ensure_profiles_schema(data)
    if changed:
        save_profiles(data)
    return data


def save_profiles(data: Dict[str, Any]) -> None:
    try:
        data.setdefault("version", PROFILE_VERSION)
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
    ensure_player_defaults(player)
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
                                  is_draw: bool,
                                  ai_level_index: Optional[int] = None,
                                  human_side: Side = HUMAN_SIDE) -> None:
    if mode not in ("pvp", "ai"):
        return

    def apply_pair_elo(player_a: Dict[str, Any], player_b: Dict[str, Any], result_a: str) -> None:
        rating_a = get_player_elo(player_a)
        rating_b = get_player_elo(player_b)
        update_player_elo(player_a, rating_b, result_a)
        inverse_result = "draw"
        if result_a == "win":
            inverse_result = "loss"
        elif result_a == "loss":
            inverse_result = "win"
        update_player_elo(player_b, rating_a, inverse_result)

    def get_ai_rating(level_index: Optional[int]) -> float:
        if level_index is None:
            return float(DEFAULT_ELO)
        if 0 <= level_index < len(AI_LEVELS):
            try:
                return float(AI_LEVELS[level_index].get("elo", DEFAULT_ELO))
            except Exception:
                return float(DEFAULT_ELO)
        return float(DEFAULT_ELO)

    if mode == "pvp":
        pvp_info = profiles_data.get("last_selected", {}).get("pvp", {})
        red_id = pvp_info.get("red_player_id", "p1")
        black_id = pvp_info.get("black_player_id", "p2")
        red_player = find_player(profiles_data, red_id)
        black_player = find_player(profiles_data, black_id)
        if red_player is None or black_player is None:
            return

        ensure_player_defaults(red_player)
        ensure_player_defaults(black_player)

        if is_draw or winner_side is None:
            update_stats_for_player(red_player, "draw", is_vs_ai=False)
            update_stats_for_player(black_player, "draw", is_vs_ai=False)
            apply_pair_elo(red_player, black_player, "draw")
        else:
            if winner_side == Side.RED:
                update_stats_for_player(red_player, "win", is_vs_ai=False)
                update_stats_for_player(black_player, "loss", is_vs_ai=False)
                apply_pair_elo(red_player, black_player, "win")
            else:
                update_stats_for_player(red_player, "loss", is_vs_ai=False)
                update_stats_for_player(black_player, "win", is_vs_ai=False)
                apply_pair_elo(red_player, black_player, "loss")

    elif mode == "ai":
        ai_info = profiles_data.get("last_selected", {}).get("ai", {})
        human_id = ai_info.get("human_player_id", "p1")
        human_player = find_player(profiles_data, human_id)
        if human_player is None:
            return

        ensure_player_defaults(human_player)
        ai_rating = get_ai_rating(ai_level_index)

        if is_draw or winner_side is None:
            update_stats_for_player(human_player, "draw", is_vs_ai=True)
            update_player_elo(human_player, ai_rating, "draw")
        else:
            if winner_side == human_side:
                update_stats_for_player(human_player, "win", is_vs_ai=True)
                update_player_elo(human_player, ai_rating, "win")
            else:
                update_stats_for_player(human_player, "loss", is_vs_ai=True)
                update_player_elo(human_player, ai_rating, "loss")

    save_profiles(profiles_data)
