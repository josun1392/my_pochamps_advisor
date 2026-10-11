"""Project native client-visible protocol, never simulator hidden truth.

This is a policy view using PokeAdvice's Unknown spelling, not reducer state.
Untranslated protocol events remain available to recurrent/feature encoders.
"""
from __future__ import annotations
from copy import deepcopy
import re


def unknown():
    return {"knowledge": "unknown"}


def _id(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _pokemon(identity, details=""):
    return {"identity": identity, "details": details, "current_hp": unknown(), "max_hp": unknown(),
            "hp_fraction": unknown(), "fainted": unknown(), "condition": unknown(),
            "known_item": unknown(), "current_ability": unknown(), "known_moves": [],
            "status_counter": unknown(), "stat_stages": {}}


def _condition(row, condition, *, own=False):
    parts = condition.split()
    hp = parts[0] if parts else ""
    if hp == "0":
        row.update(hp_fraction=0.0, fainted=True)
        if own:
            row["current_hp"] = 0
    elif match := re.fullmatch(r"(\d+)/(\d+)([rgy]?)", hp):
        numerator, denominator = map(int, match.group(1, 2))
        row.update(hp_fraction=numerator / denominator, fainted=False)
        if own:
            row.update(current_hp=numerator, max_hp=denominator)
    row["condition"] = next((p for p in parts[1:] if p != "fnt"), None)
    row["hp_display"] = hp  # Champions floor percentage and colour, not exact HP


def project_policy_observation(native: dict, history: list[str]) -> dict:
    """Only accepts the separate native policy channel object, not checkpoints."""
    if native.get("schema_version") != "showdown-policy-observation-v1":
        raise ValueError("invalid_policy_observation")
    role = "p1" if native["side"] == "self" else "p2"
    sides = {s: {"active_identity": unknown(), "pokemon": {}, "preview": []} for s in ("p1", "p2")}
    field = {"weather": unknown(), "terrain": unknown()}
    for line in history:
        parts = line.split("|")
        if len(parts) < 2:
            continue
        kind, args = parts[1], parts[2:]
        if kind == "start":
            field.update(weather=None, terrain=None)
        if kind == "poke" and len(args) >= 2 and args[0] in sides:
            sides[args[0]]["preview"].append({"details": args[1]})
        if kind == "-weather" and args:
            field["weather"] = None if args[0] == "none" else _id(args[0])
        if kind in {"-fieldstart", "-fieldend"} and args and "terrain" in args[0].lower():
            field["terrain"] = _id(args[0].removeprefix("move: ")) if kind == "-fieldstart" else None
        if kind == "-clearallboost":
            # Native Haze announces one global event with no Pokemon argument.
            # Project the public reset; never recalculate any battle mechanic.
            for public_side in sides.values():
                active = public_side["active_identity"]
                if isinstance(active, str) and active in public_side["pokemon"]:
                    public_side["pokemon"][active]["stat_stages"] = {}
            continue
        if not args or not re.match(r"^p[12][a-z]?: ", args[0]):
            continue
        identity = args[0]
        side = sides[identity[:2]]
        row = side["pokemon"].setdefault(identity, _pokemon(identity))
        if kind in {"switch", "drag", "replace"} and len(args) >= 3:
            row["details"] = args[1]
            side["active_identity"] = identity
            _condition(row, args[2], own=identity[:2] == role)
            row["stat_stages"] = {}
        elif kind in {"-damage", "-heal", "-sethp"} and len(args) >= 2:
            _condition(row, args[1], own=identity[:2] == role)
        elif kind == "faint":
            row.update(fainted=True, hp_fraction=0.0)
        elif kind == "-status" and len(args) >= 2:
            row["condition"] = args[1]
        elif kind == "-curestatus":
            row["condition"] = None
        elif kind == "-item" and len(args) >= 2:
            row["known_item"] = _id(args[1])
        elif kind == "-enditem":
            row["known_item"] = None
        elif kind == "-mega" and len(args) >= 3:
            row["known_item"] = _id(args[2])
        elif kind in {"detailschange", "-formechange"} and len(args) >= 2:
            row["details"] = args[1] if kind == "detailschange" else args[1] + ("," + row["details"].split(",", 1)[1] if "," in row["details"] else "")
        elif kind == "-ability" and len(args) >= 2:
            row["current_ability"] = _id(args[1])
        elif kind == "move" and len(args) >= 2 and not any(a.startswith("[from]") for a in args):
            move = _id(args[1])
            if move not in row["known_moves"]:
                row["known_moves"].append(move)
        elif kind in {"-boost", "-unboost", "-setboost"} and len(args) >= 3:
            stat, amount = args[1], int(args[2])
            row["stat_stages"][stat] = amount if kind == "-setboost" else row["stat_stages"].get(stat, 0) + (amount if kind == "-boost" else -amount)
        elif kind == "-clearboost":
            row["stat_stages"] = {}
        elif kind in {"-clearpositiveboost", "-clearnegativeboost"}:
            clamp = min if kind == "-clearpositiveboost" else max
            row["stat_stages"] = {stat: clamp(stage, 0) for stat, stage in row["stat_stages"].items()}
        elif kind == "-invertboost":
            row["stat_stages"] = {stat: -stage for stat, stage in row["stat_stages"].items()}
        # Items/abilities attributed directly to this public target are revealed.
        if not any(a.startswith("[of]") for a in args):
            for arg in args:
                if arg.startswith("[from] item: "):
                    row["known_item"] = _id(arg.removeprefix("[from] item: "))
                elif arg.startswith("[from] ability: "):
                    row["current_ability"] = _id(arg.removeprefix("[from] ability: "))
    own = sides[role]
    for pokemon in native["own_request"].get("side", {}).get("pokemon", []):
        # Native own-request ident omits the active-position letter.
        name = pokemon["ident"].split(": ", 1)[1]
        identity = next((key for key in own["pokemon"] if key.split(": ", 1)[1] == name), pokemon["ident"])
        row = own["pokemon"].setdefault(identity, _pokemon(identity, pokemon["details"]))
        row["details"] = pokemon["details"]
        _condition(row, pokemon["condition"], own=True)
        item = pokemon.get("item", unknown())
        ability = pokemon.get("ability", unknown())
        row.update(known_item=(item or None) if isinstance(item, str) else row["known_item"],
                   current_ability=ability if isinstance(ability, str) and ability else row["current_ability"],
                   known_moves=list(pokemon.get("moves", [])))
        if pokemon.get("active"):
            own["active_identity"] = identity
    for health in native.get("visible_active_health", []):
        identity = health["identity"]
        row = sides[identity[:2]]["pokemon"].setdefault(identity, _pokemon(identity))
        _condition(row, health["condition"], own=identity[:2] == role)
    result = deepcopy(native)
    result["interpretation"] = "hypothetical_player_visible_observation_not_live_truth"
    result["public_history"] = list(history)
    result["state"] = {"state_version": "showdown-policy-state-v1", "self_side": sides[role],
                       "opponent_side": sides["p2" if role == "p1" else "p1"], "field": field}
    return result
