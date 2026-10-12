"""Versioned, role-conditioned hypothetical sets; native M-C validates legality.

Coverage fixtures, not ladder usage or optimal team labels. No cross-version
rewriting of previous curricula; old species-disjoint final pools stay unseen.
"""

import random
from hashlib import sha256
from advisor.learned_roster import BROAD_TRAIN, BROAD_UNSEEN, _parse
from advisor.learned_scenarios import TRAIN

VERSION = "showdown-learning-curriculum-v5"
EXTRA_TRAIN = _parse("""
Empoleon|Torrent|Surf,Flash Cannon,Ice Beam,Stealth Rock|spa|
Heracross|Guts|Close Combat,Megahorn,Rock Blast,Swords Dance|atk|Heracronite
Ninetales-Alola|Snow Warning|Blizzard,Moonblast,Aurora Veil,Encore|spa|
Snorlax|Thick Fat|Body Slam,Crunch,Rest,Curse|spd|
Weavile|Pressure|Icicle Crash,Knock Off,Ice Shard,Swords Dance|atk|
Mamoswine|Thick Fat|Earthquake,Icicle Crash,Ice Shard,Stealth Rock|atk|
Gallade|Sharpness|Psycho Cut,Sacred Sword,Leaf Blade,Swords Dance|atk|Galladite
Baxcalibur|Thermal Exchange|Glaive Rush,Icicle Crash,Ice Shard,Dragon Dance|atk|
Tinkaton|Mold Breaker|Gigaton Hammer,Play Rough,Knock Off,Thunder Wave|atk|
Cinderace|Libero|Pyro Ball,High Jump Kick,U-turn,Court Change|atk|
Golisopod|Emergency Exit|First Impression,Liquidation,Leech Life,Aqua Jet|atk|
Tsareena|Queenly Majesty|Power Whip,High Jump Kick,U-turn,Synthesis|atk|
Sneasler|Poison Touch|Dire Claw,Close Combat,U-turn,Swords Dance|atk|
Glimmora|Toxic Debris|Power Gem,Sludge Wave,Earth Power,Mortal Spin|spa|
Maushold|Technician|Population Bomb,Crunch,Encore,Tidy Up|atk|
""")
EXTRA_UNSEEN = _parse("""
Hawlucha|Unburden|Acrobatics,Close Combat,Swords Dance,Roost|atk|
Aegislash|Stance Change|Shadow Ball,Flash Cannon,Shadow Sneak,King's Shield|spa|
Goodra-Hisui|Sap Sipper|Dragon Pulse,Flash Cannon,Thunderbolt,Rest|spd|
Steelix|Sturdy|Earthquake,Heavy Slam,Stealth Rock,Body Press|def|Steelixite
Sceptile|Overgrow|Leaf Storm,Dragon Pulse,Focus Blast,Substitute|spa|Sceptilite
Feraligatr|Sheer Force|Waterfall,Ice Punch,Crunch,Dragon Dance|atk|
""")


def coherent_case(split, index):
    seed = int.from_bytes(sha256(f"{VERSION}:{split}:{index}".encode()).digest(), "big")
    rng = random.Random(seed)
    pool = (
        BROAD_UNSEEN + EXTRA_UNSEEN
        if split == "unseen"
        else TRAIN + BROAD_TRAIN + EXTRA_TRAIN
    )
    teams, preview = {}, {}
    for side in ("self", "opponent"):
        groups = [[p for p in pool if p[3] == role] for role in ("atk", "spa")]
        groups.append([p for p in pool if p[3] in {"def", "spd"}])
        chosen = []
        for group in groups:
            for _ in range(2):
                used_species = {p[0].split("-")[0] for p in chosen}
                chosen.append(
                    rng.choice(
                        [p for p in group if p[0].split("-")[0] not in used_species]
                    )
                )
        rng.shuffle(chosen)
        used, mega, team = set(), False, []
        for species, ability, moves, investment, stone in chosen:
            support = investment in {"def", "spd"}
            # Choice items are deliberately absent from mixed support/setup sets.
            items = (
                ["Leftovers", "Sitrus Berry", "Rocky Helmet", "Lum Berry", ""]
                if support
                else [
                    "Life Orb",
                    "Focus Sash",
                    "Expert Belt",
                    "Lum Berry",
                    "Sitrus Berry",
                    "",
                ]
            )
            options = [i for i in items if not i or i not in used]
            item = rng.choice(options)
            # Toxic Orb is absent in the pinned M-C item pool; do not invent it.
            if species == "Gliscor":
                ability = "Hyper Cutter"
            if stone and not mega and rng.random() < 0.5:
                item, mega = stone, True
            if item:
                used.add(item)
            moves = list(moves)
            rng.shuffle(moves)
            fast = not support and rng.random() < 0.65
            team.append(
                {
                    "species": species,
                    "ability": ability,
                    "moves": moves,
                    "item": item,
                    "level": 50,
                    "nature": ("Timid" if fast else "Modest")
                    if investment == "spa"
                    else ("Jolly" if fast else "Adamant")
                    if investment == "atk"
                    else "Bold"
                    if investment == "def"
                    else "Calm",
                    "evs": {
                        investment: 32,
                        "spe" if fast else "hp": 32,
                        "hp" if fast else "spe": 2,
                    },
                }
            )
        teams[side] = team
        # One of each broad role, shuffled: avoids randomly excluding all defenses.
        selection = [
            rng.choice([i + 1 for i, p in enumerate(chosen) if p[3] == role])
            for role in ("atk", "spa")
        ]
        selection.append(
            rng.choice([i + 1 for i, p in enumerate(chosen) if p[3] in {"def", "spd"}])
        )
        rng.shuffle(selection)
        preview[side] = selection
    return {
        "scenario_id": f"{split}-{index}",
        "teams": teams,
        "preview": preview,
        "seed": [rng.randrange(65536) for _ in range(4)],
        "history": [],
        "assumptions": [
            "Complete role-conditioned hypothetical teams, never observed truth."
        ],
    }
