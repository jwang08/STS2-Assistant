"""Save file reader for STS2 progress, run history, and current run."""
import json
import logging
import pathlib
from pathlib import Path

from model import CurrentRun, RunFloor, RunHistory

log = logging.getLogger(__name__)

SAVE_DIR = "C:/Users/coolg/AppData/Roaming/SlayTheSpire2/steam/76561198278610616/profile1/saves"

# Characters
CHARACTERS = ["Ironclad", "Silent", "Defect", "Necrobinder", "Regent"]
CHARACTER_IDS = {
    "CHARACTER.IRONCLAD": "Ironclad",
    "CHARACTER.SILENT": "Silent",
    "CHARACTER.DEFECT": "Defect",
    "CHARACTER.NECROBINDER": "Necrobinder",
    "CHARACTER.REGENT": "Regent",
}

def _read_json(path: Path) -> dict | None:
    try:
        if pathlib.Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to read %s: %s", path, e)
    return None


def _get_player(players: list[dict], index: int = 0) -> dict:
    """Get a player by index from the player list. Falls back to first player."""
    if not players:
        return {}
    if 0 <= index < len(players):
        return players[index]
    return players[0]


def _get_player_stats(player_stats: list[dict], player: dict) -> dict:
    """Find matching player stats for a floor. Returns {} when no match — co-op
    runs must not cross-contaminate by returning the wrong player's stats."""
    player_id = str(player.get("id", ""))
    for ps in player_stats:
        if str(ps.get("player_id", "")) == player_id:
            return ps
    return {}


def get_current_run(player_index: int = 0) -> CurrentRun:
    """Read the current active run, if any. Use player_index for co-op."""
    # Prefer live save files; fall back to backups (picking most recent)
    data = None
    for fname in ("current_run.save", "current_run_mp.save"):
        data = _read_json(SAVE_DIR + "/history" +fname)
        if data:
            break

    if not data:
        # No live file — check backups, pick the most recently saved.
        # Only use a backup if the run hasn't already finished (i.e. its
        # start_time doesn't appear as a history file).
        history_dir = SAVE_DIR + "/history"
        history_starts: set[str] = set()
        if pathlib.Path(history_dir).exists():
            history_starts = {p.stem for p in Path(history_dir).iterdir() if p.suffix == ".run"}
        best, best_time = None, 0
        for fname in ("current_run.save.backup", "current_run_mp.save.backup"):
            candidate = _read_json(SAVE_DIR +"/"+ fname)
            if not candidate:
                continue
            start = str(candidate.get("start_time", ""))
            if start in history_starts:
                continue  # This run already finished
            try:
                save_time = int(candidate.get("save_time") or 0)
            except (TypeError, ValueError):
                save_time = 0
            if save_time > best_time:
                best = candidate
                best_time = save_time
        if best:
            data = best

    if not data:
        return CurrentRun(active=False)

    players = data.get("players", [])
    player = _get_player(players, player_index)
    character = CHARACTER_IDS.get(
        player.get("character_id", player.get("character", "")),
        player.get("character_id", "Unknown"),
    )
    # Filter empty IDs: malformed entries would pollute analytics with "" keys.
    deck_entries = [c for c in player.get("deck", []) if c.get("id")]
    deck = [c.get("id", "") for c in deck_entries]
    deck_upgrades = [(c.get("upgrade_count") or 0) > 0 for c in deck_entries]
    relics = [r.get("id", "") for r in player.get("relics", []) if r.get("id")]
    potions = [p.get("id", "") for p in player.get("potions", []) if p.get("id")]

    # Parse floor history
    floors = []
    floor_num = 0
    for act_floors in data.get("map_point_history", []):
        for floor_data in act_floors:
            floor_num += 1
            rooms = floor_data.get("rooms", [])
            room = rooms[0] if rooms else {}
            p_stats = _get_player_stats(
                floor_data.get("player_stats", []), player
            )
            card_picked = ""
            for cc in p_stats.get("card_choices", []):
                if cc.get("was_picked"):
                    card_picked = cc.get("card", {}).get("id", "")
            floors.append(RunFloor(
                floor=floor_num,
                type=floor_data.get("map_point_type", room.get("room_type", "")),
                encounter=room.get("model_id", ""),
                monsters=room.get("monster_ids", []),
                turns=room.get("turns_taken", 0),
                damage_taken=p_stats.get("damage_taken", 0),
                hp_healed=p_stats.get("hp_healed", 0),
                current_hp=p_stats.get("current_hp", 0),
                max_hp=p_stats.get("max_hp", 0),
                gold=p_stats.get("current_gold", 0),
                card_picked=card_picked,
            ))

    return CurrentRun(
        active=True,
        character=character,
        current_hp=player.get("current_hp", 0),
        max_hp=player.get("max_hp", 0),
        gold=player.get("gold", 0),
        act=(data.get("current_act_index") or 0) + 1,
        floor=floor_num,
        deck=deck,
        deck_upgrades=deck_upgrades,
        relics=relics,
        potions=potions,
        events_seen=data.get("events_seen", []),
        floors=floors,
    )


def get_run_history() -> list[RunHistory]:
    """Read all completed run history files."""
    history_dir = SAVE_DIR + "/history"
    if not pathlib.Path(history_dir).exists():
        return []
        

    runs = []
    for run_file in sorted(pathlib.Path(history_dir).glob("*.run"), reverse=True):
        try:
            data = _read_json(run_file)
            if not data:
                print("wawa")
                continue

            players = data.get("players", [])
            player = _get_player(players)

            # History files use "character"; current_run files use "character_id".
            # Try both to keep per-character analytics consistent across both.
            char_key = player.get("character_id") or player.get("character", "")
            character = CHARACTER_IDS.get(char_key, char_key or "Unknown")
            deck = [c.get("id", "") for c in player.get("deck", []) if c.get("id")]
            relics = [r.get("id", "") for r in player.get("relics", []) if r.get("id")]

            # Parse floor history
            floors = []
            floor_num = 0
            for act_floors in data.get("map_point_history", []):
                for floor_data in act_floors:
                    floor_num += 1
                    rooms = floor_data.get("rooms", [])
                    room = rooms[0] if rooms else {}

                    p_stats = _get_player_stats(
                        floor_data.get("player_stats", []), player
                    )

                    card_picked = ""
                    cards_offered = []
                    for cc in p_stats.get("card_choices", []):
                        card_info = cc.get("card", {})
                        cid = card_info.get("id", "")
                        if not cid:
                            continue  # skip empty IDs — they pollute pick-rate counters
                        cards_offered.append(cid)
                        if cc.get("was_picked"):
                            card_picked = cid

                    floors.append(RunFloor(
                        floor=floor_num,
                        type=floor_data.get("map_point_type", room.get("room_type", "")),
                        encounter=room.get("model_id", ""),
                        monsters=room.get("monster_ids", []),
                        turns=room.get("turns_taken", 0),
                        damage_taken=p_stats.get("damage_taken", 0),
                        hp_healed=p_stats.get("hp_healed", 0),
                        current_hp=p_stats.get("current_hp", 0),
                        max_hp=p_stats.get("max_hp", 0),
                        gold=p_stats.get("current_gold", 0),
                        cards_offered=cards_offered,
                        card_picked=card_picked,
                        potions_used=[p for p in p_stats.get("potion_used", []) if p],
                        potions_gained=[p.get("choice", "") for p in p_stats.get("potion_choices", []) if p.get("was_picked") and p.get("choice")],
                    ))

            # Timestamp: prefer start_time from data, fallback to filename
            timestamp = data.get("start_time", 0)
            if not timestamp:
                try:
                    timestamp = int(run_file.stem)
                except (ValueError, TypeError):
                    timestamp = 0

            runs.append(RunHistory(
                id=run_file.stem,
                character=character,
                win=data.get("win", False),
                ascension=data.get("ascension", 0),
                seed=data.get("seed", ""),
                acts=data.get("acts", []),
                killed_by=data.get("killed_by_encounter", ""),
                run_time=data.get("run_time", 0),
                deck=deck,
                relics=relics,
                floors=floors,
                build_id=data.get("build_id", ""),
                timestamp=timestamp,
                total_players=len(players),
            ))
        except Exception as e:
            log.warning("Failed to parse run file %s: %s", run_file.name, e)

    return runs