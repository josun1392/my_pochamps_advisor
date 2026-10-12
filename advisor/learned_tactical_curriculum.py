"""V4 coordinator-only tactical starts, progressed exclusively by native choices.

Labels, complete sets and scripted prefixes never enter policy observations.
Half the train/validation/test cases remain broad; unseen is species-disjoint.
Motifs are coverage fixtures, not oracle labels or guaranteed optimal actions.
"""

from copy import deepcopy
from hashlib import sha256
import random
from advisor.learned_encoder import identifier
from advisor.learned_roster import BROAD_TRAIN
from advisor.learned_scenarios import TRAIN

VERSION = "showdown-learning-curriculum-v4"
# Opposing examples intentionally include tempting but unsafe tactical actions.
MOTIFS = (
    ("switch_fire", "Scizor", "Arcanine", "Rotom-Wash", ()),
    ("stay_fairy", "Scizor", "Sylveon", "Rotom-Wash", ()),
    ("switch_grass", "Slowbro", "Meowscarada", "Corviknight", ()),
    ("stay_fighting", "Slowbro", "Lucario", "Corviknight", ()),
    ("setup_water", "Gyarados", "Blastoise", "Scizor", ()),
    ("setup_fairy_risk", "Dragonite", "Sylveon", "Scizor", ()),
    ("setup_dragon", "Clefable", "Garchomp", "Slowbro", ()),
    ("setup_steel_risk", "Clefable", "Metagross", "Slowbro", ()),
    (
        "recover_resisted",
        "Slowbro",
        "Metagross",
        "Corviknight",
        (("raindance", "bulletpunch"),) * 6,
    ),
    (
        "recover_grass_risk",
        "Slowbro",
        "Metagross",
        "Corviknight",
        (("raindance", "bulletpunch"),) * 6 + (("raindance", "switch:Meowscarada"),),
    ),
    (
        "defend_physical",
        "Corviknight",
        "Garchomp",
        "Slowbro",
        (("defog", "dragonclaw"),) * 3,
    ),
    (
        "defend_fire_risk",
        "Corviknight",
        "Garchomp",
        "Slowbro",
        (("defog", "dragonclaw"),) * 3 + (("defog", "switch:Arcanine"),),
    ),
)


def tactical_case(split, index):
    from advisor.learned_scenarios import scenario

    seed = int.from_bytes(sha256(f"{VERSION}:{split}:{index}".encode()).digest(), "big")
    case = scenario(split, seed, version="showdown-learning-curriculum-v3")
    case["scenario_id"] = f"{VERSION}:{split}:{index}"
    if split == "unseen" or index % 2:
        return case
    label, own, other, bench, prefix = MOTIFS[(index // 2) % len(MOTIFS)]
    rng = random.Random(seed)
    pool = {p[0]: p for p in TRAIN + BROAD_TRAIN}

    def build(lead, reserve, third):
        names = [lead, reserve, third]
        names += rng.sample([s for s in pool if s not in names], 3)
        result = []
        for species in names:
            _, ability, moves, investment, _ = pool[species]
            moves = list(moves)
            if species == "Slowbro":
                moves = ["Surf", "Slack Off", "Thunder Wave", "Rain Dance"]
            if species == "Corviknight":
                moves = ["Brave Bird", "Roost", "Iron Defense", "Defog"]
            rng.shuffle(moves)
            result.append(
                dict(
                    species=species,
                    ability=ability,
                    moves=moves,
                    item="",
                    level=50,
                    nature="Modest"
                    if investment == "spa"
                    else "Adamant"
                    if investment == "atk"
                    else "Bold",
                    evs={investment: 32, "hp": 32, "spe": 2},
                )
            )
        return result

    case["teams"] = {
        "self": build(
            own,
            bench,
            "Garchomp" if own != "Garchomp" and bench != "Garchomp" else "Gengar",
        ),
        "opponent": build(
            other,
            "Meowscarada" if other != "Meowscarada" else "Arcanine",
            "Arcanine" if other not in {"Arcanine", "Meowscarada"} else "Toxapex",
        ),
    }
    case["preview"] = {side: [1, 2, 3] for side in case["teams"]}
    case["learning_start"] = {"motif": label, "prefix": prefix}
    return case


def reset_learning_episode(env, case):
    """Apply legal prefix through the same native API used during agent execution."""
    case = deepcopy(case)
    start = case.pop("learning_start", {})
    env.reset(case)
    executed = 0
    for pair in start.get("prefix", ()):
        views = {
            s: env.observation(s, include_history=True) for s in ("self", "opponent")
        }
        if any(v["request_state"] != "move" for v in views.values()):
            break  # A native critical hit/faint can produce a valid replacement start.
        actions = {}
        for side, move_id in zip(views, pair):
            v = views[side]
            if move_id.startswith("switch:"):
                species = identifier(move_id.split(":", 1)[1])
                choices = [
                    i
                    for i, p in enumerate(v["own_request"]["side"]["pokemon"])
                    if identifier(p["details"]) == species and v["action_mask"][i]
                ]
            else:
                choices = [
                    6 + i
                    for i, m in enumerate(v["own_request"]["active"][0]["moves"])
                    if m["id"] == move_id and v["action_mask"][6 + i]
                ]
            if not choices:
                raise ValueError("illegal_tactical_prefix")
            actions[side] = choices[0]
        result = env.step(actions, revision=views["self"]["revision"])
        executed += 1
        if result["terminated"] or result["truncated"]:
            raise ValueError("tactical_prefix_ended_episode")
    return {"motif": start.get("motif", "broad"), "prefix_decisions": executed}
