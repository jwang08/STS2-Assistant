import save
from model import RunHistory
import calc
import json

def compute_aggregate_stats(runs: list[RunHistory]) -> dict:
    """Extract aggregate stats from runs. Excludes PII (seed, id, floors, full decks)."""
    card_pick_rates: dict[str, dict] = {}
    card_win_rates: dict[str, dict] = {}
    relic_win_rates: dict[str, dict] = {}
    character_stats: dict[str, dict] = {}
    ascension_stats: dict[int, dict] = {}

    for run in runs:
        # Character stats
        cs = character_stats.setdefault(run.character, {"wins": 0, "total": 0})
        cs["total"] += 1
        if run.win:
            cs["wins"] += 1

        # Ascension stats
        ast = ascension_stats.setdefault(run.ascension, {"wins": 0, "total": 0})
        ast["total"] += 1
        if run.win:
            ast["wins"] += 1

        # Card win rates (from final deck)
        for card_id in set(run.deck):
            cw = card_win_rates.setdefault(card_id, {"wins": 0, "total": 0})
            cw["total"] += 1
            if run.win:
                cw["wins"] += 1

        # Relic win rates
        for relic_id in set(run.relics):
            rw = relic_win_rates.setdefault(relic_id, {"wins": 0, "total": 0})
            rw["total"] += 1
            if run.win:
                rw["wins"] += 1

        # Card pick rates (from floor data)
        for floor in run.floors:
            if floor.cards_offered:
                for offered_id in floor.cards_offered:
                    if offered_id:
                        cp = card_pick_rates.setdefault(offered_id, {"picked": 0, "offered": 0})
                        cp["offered"] += 1
                if floor.card_picked:
                    cp = card_pick_rates.setdefault(floor.card_picked, {"picked": 0, "offered": 0})
                    cp["picked"] += 1

    return {
        "run_count": len(runs),
        "card_pick_rates": card_pick_rates,
        "card_win_rates": card_win_rates,
        "relic_win_rates": relic_win_rates,
        "character_stats": character_stats,
        "ascension_stats": {str(k): v for k, v in ascension_stats.items()},
    }

print(save.SAVE_DIR)

print("Loading run history...")
runs = save.get_run_history()
print(f"Found {len(runs)} runs, computing stats...")
stats = compute_aggregate_stats(runs)
print(f"Exported stats from {stats.get('run_count', 0)} runs.")


data = calc.compute_analytics(runs)

json_str = json.dumps(data, indent=4)
with open("sample.json", "w") as f:
    f.write(json_str)

data = save.get_current_run()

json_str = json.dumps(data.model_dump(), indent=4)
with open("current.json", "w") as f:
    f.write(json_str)