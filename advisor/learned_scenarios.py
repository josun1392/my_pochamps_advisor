"""Explicit hypothetical M-C curricula and a species-disjoint unseen split.

The coordinator sees sets and seeds. Policies never receive this module's output.
Native TeamValidator remains the legality authority.
"""

import random
from hashlib import sha256

TRAIN = [
    (
        "Charizard",
        "Blaze",
        ["Flamethrower", "Air Slash", "Dragon Pulse", "Protect"],
        "spa",
        "Charizardite X",
    ),
    (
        "Scizor",
        "Technician",
        ["Bullet Punch", "U-turn", "Close Combat", "Swords Dance"],
        "atk",
        "Scizorite",
    ),
    (
        "Garchomp",
        "Rough Skin",
        ["Earthquake", "Dragon Claw", "Rock Slide", "Protect"],
        "atk",
        "",
    ),
    (
        "Rotom-Wash",
        "Levitate",
        ["Hydro Pump", "Thunderbolt", "Volt Switch", "Will-O-Wisp"],
        "spa",
        "",
    ),
    (
        "Tyranitar",
        "Sand Stream",
        ["Crunch", "Rock Slide", "Earthquake", "Protect"],
        "atk",
        "Tyranitarite",
    ),
    (
        "Dragonite",
        "Inner Focus",
        ["Dragon Claw", "Extreme Speed", "Earthquake", "Dragon Dance"],
        "atk",
        "",
    ),
    (
        "Gengar",
        "Cursed Body",
        ["Shadow Ball", "Sludge Bomb", "Thunderbolt", "Protect"],
        "spa",
        "Gengarite",
    ),
    (
        "Venusaur",
        "Overgrow",
        ["Giga Drain", "Sludge Bomb", "Earth Power", "Protect"],
        "spa",
        "Venusaurite",
    ),
    (
        "Gyarados",
        "Intimidate",
        ["Waterfall", "Ice Fang", "Earthquake", "Dragon Dance"],
        "atk",
        "Gyaradosite",
    ),
    (
        "Lucario",
        "Inner Focus",
        ["Close Combat", "Extreme Speed", "Bullet Punch", "Swords Dance"],
        "atk",
        "Lucarionite",
    ),
]
UNSEEN = [
    (
        "Blastoise",
        "Torrent",
        ["Hydro Pump", "Ice Beam", "Dark Pulse", "Protect"],
        "spa",
        "Blastoisinite",
    ),
    (
        "Gardevoir",
        "Trace",
        ["Moonblast", "Psychic", "Thunderbolt", "Protect"],
        "spa",
        "Gardevoirite",
    ),
    (
        "Metagross",
        "Clear Body",
        ["Meteor Mash", "Zen Headbutt", "Bullet Punch", "Protect"],
        "atk",
        "Metagrossite",
    ),
    (
        "Sylveon",
        "Pixilate",
        ["Hyper Voice", "Moonblast", "Shadow Ball", "Protect"],
        "spa",
        "",
    ),
    (
        "Salamence",
        "Intimidate",
        ["Dragon Claw", "Flamethrower", "Earthquake", "Dragon Dance"],
        "atk",
        "Salamencite",
    ),
    (
        "Swampert",
        "Torrent",
        ["Waterfall", "Earthquake", "Ice Punch", "Protect"],
        "atk",
        "Swampertite",
    ),
]


def scenario(split, index, *, version="showdown-learning-curriculum-v1"):
    if split not in {"train", "validation", "test", "unseen"}:
        raise ValueError("invalid_curriculum_split")
    if version == "showdown-learning-curriculum-v1":
        seed = {
            "train": 100000,
            "validation": 200000,
            "test": 300000,
            "unseen": 400000,
        }[split] + index
    elif version in {
        "showdown-learning-curriculum-v2",
        "showdown-learning-curriculum-v3",
    }:
        seed = int.from_bytes(
            sha256(f"{version}:{split}:{index}".encode()).digest(), "big"
        )
    else:
        raise ValueError("unsupported_learning_curriculum")
    rng = random.Random(seed)
    pool = UNSEEN if split == "unseen" else TRAIN
    if version == "showdown-learning-curriculum-v3":
        from advisor.learned_roster import BROAD_TRAIN, BROAD_UNSEEN

        pool = BROAD_UNSEEN if split == "unseen" else TRAIN + BROAD_TRAIN
    teams = {}
    for side in ("self", "opponent"):
        chosen = rng.sample(pool, 6)
        items = ["", "", "Focus Sash", "Sitrus Berry", "Life Orb", "Leftovers"]
        if version == "showdown-learning-curriculum-v3":
            items = rng.sample(
                [
                    "",
                    "Focus Sash",
                    "Sitrus Berry",
                    "Life Orb",
                    "Leftovers",
                    "Rocky Helmet",
                    "Lum Berry",
                    "Choice Scarf",
                    "Expert Belt",
                ],
                6,
            )
        rng.shuffle(items)
        team = []
        mega_used = False
        for (species, ability, moves, attack, stone), item in zip(chosen, items):
            if stone and not mega_used and rng.random() < 0.4:
                item, mega_used = stone, True
            moves = list(moves)
            rng.shuffle(moves)
            fast = rng.random() < 0.5 and attack in {"atk", "spa"}
            team.append(
                {
                    "species": species,
                    "ability": ability,
                    "moves": moves,
                    "item": item,
                    "level": 50,
                    "nature": ("Timid" if fast else "Modest")
                    if attack == "spa"
                    else ("Jolly" if fast else "Adamant")
                    if attack == "atk"
                    else "Bold"
                    if attack == "def"
                    else "Calm",
                    "evs": {
                        attack: 32,
                        "spe" if fast else "hp": 32,
                        "hp" if fast else "spe": 2,
                    },
                }
            )
        teams[side] = team
    return {
        "scenario_id": f"{split}-{index}",
        "teams": teams,
        "seed": [rng.randrange(65536) for _ in range(4)],
        "preview": {side: rng.sample(range(1, 7), 3) for side in teams},
        "history": [],
        "assumptions": [
            "Complete hypothetical teams, sets and selections; never live observed truth."
        ],
    }
