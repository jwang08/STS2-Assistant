import ollama
import json
import chromadb
from ollama import chat


with open('sample.json') as f:
    data = json.load(f)
keys = [
    ("overview", 0),
    ("win_trend", 0),
    ("ascension_curve", 0),
    ("character_breakdown", 0),
    ("card_rankings", 1),
    ("card_pick_rates", 1),
    ("card_quality", 1),
    ("card_pick_timing", 1),
    ("card_regret", 1),
    ("synergy_edges", 1),
    ("relic_rankings", 2),
    ("relic_rankings_by_character", 2),
    ("relic_synergy_edges", 2),
    ("deadly_encounters", 3),
    ("damage_percentiles", 3),
    ("encounter_danger", 3),
    ("floor_survival", 4),
    ("death_floors", 4),
    ("hp_tracking", 4),
    ("damage_by_act", 4),
    ("per_act", 4),
    ("gold_economy", 5),
    ("potion_stats", 5),
    ("healing_sources", 5),
    ("turn_efficiency", 6),
    ("winning_deck_traits", 6),
    ("archetype_stats", 6),
    ("coop_stats", 6),
]

documents = [
    """Run Overview
    overview - aggregate stats: total runs, wins, losses, win rate, avg deck size, avg floors reached, avg time
    win_trend - rolling 10-run win rate over time, showing how performance has changed across your history
    ascension_curve - win rate broken down by ascension level
    character_breakdown - wins/losses/win rate/avg deck size per character""",
    """Cards: always use when dealing with cards
    card_rankings - every card ranked by win rate (runs won when the card was in the deck)
    card_pick_rates - how often each card was picked vs. offered
    card_quality - combined pick rate + win rate per card (the "is this card actually good" view)
    card_pick_timing - which cards get picked early, mid, or late in a run
    card_regret - cards skipped most often in winning runs, picked most often in losing runs, and a composite "regret score"
    synergy_edges - pairs of cards that frequently appear together in the same deck, weighted by co-occurrence count""",
    """Relics
    relic_rankings - relics ranked by win rate across all characters
    relic_rankings_by_character - same but split per character
    relic_synergy_edges - relic pairs that frequently appear together""",
    """Encounters
    deadly_encounters - encounters sorted by avg damage dealt and death count
    damage_percentiles - p25/median/p75 damage distribution per encounter
    encounter_danger - every encounter graded Low/Medium/High/Extreme by avg damage and kill rate""",
    """Run Progression
    floor_survival - how many runs ended in each floor range (bucketed by 5)
    death_floors - exact floors where deaths occur most
    hp_tracking - avg HP% per floor, split between eventual wins and losses
    damage_by_act - avg damage taken per floor and max hit per act
    per_act - cards added, avg gold, death count, and avg damage per act""",
    """Economy & Resources
    gold_economy - avg gold per run, gold curve by floor, win vs loss gold comparison
    potion_stats - usage count, win rate when used, and gain vs use rate per potion
    healing_sources - total healing broken down by rest sites, combat healing, and other sources""",
    """Other
    turn_efficiency - avg turns per fight/elite/boss, and a turns-vs-damage correlation
    winning_deck_traits - avg deck size, relic count, floors, and time for wins vs losses
    archetype_stats - empty in your data, presumably meant for deck archetype classification
    coop_stats - co-op run count and win rate vs solo win rate"""
]

client = chromadb.Client()
collection = client.create_collection(name="docs")

# store each document in a vector embedding database
for i, d in enumerate(documents):
  response = ollama.embed(model="mxbai-embed-large", input=d)
  embeddings = response["embeddings"]
  collection.add(
    ids=[str(i)],
    embeddings=embeddings,
    documents=[d]
  )

# an example input
userIn = "Should I take prepared or acrobatics card" #"Should I take the Booming Conch, Scroll of Boxes, or Cursed Pearl as the Silent?"

# generate an embedding for the input and retrieve the most relevant doc
response = ollama.embed(
  model="mxbai-embed-large",
  input=userIn
)
results = collection.query(
  query_embeddings=response["embeddings"],
  n_results=1
)
relevantCollectionIndex = documents.index(results['documents'][0][0])

nameList = []
for name, indexes in keys:
   if(relevantCollectionIndex == indexes):
        nameList.append(name)

#print(nameList)

usefulDocs = []
for name in nameList:
    usefulDocs.append(data[name])

response = chat(
    model='ALIENTELLIGENCE/aidatascientistv2',
    messages=[{
        "role": "system",
        "content": "You are a card game advisor to give general advice. Answer questions using ONLY the context provided. If the statistics is not in the context, say you don't know. Do not make up stats or card names."
    },
    {
        "role": "system",
        "content": f"Rules: ONLY use this data for decisions:{usefulDocs}, Only return short answers followed by an explanation ONLY from the data, the format for the data is name followed by it's related statitics, for synergies it's the first item, then the second, then their compatiability"
    },
    {'role': 'user', 'content': f'Question: {userIn}'}
    ],)
print(response.message.content)