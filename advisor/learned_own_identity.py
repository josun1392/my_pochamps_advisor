"""Own-player identity reconciliation using authoritative visible own requests.

Only the new categorical contract uses this adapter. Opponent appearances and
historical public projections/replays are untouched. No native hidden state.
"""
from copy import deepcopy
from advisor.showdown_observation import _condition
from advisor.learned_encoder import identifier


def _empty_unpositioned_reference(key, row, role):
    # Native hitcount can refer to a fainted Pokemon as `p1: name` after the
    # positioned faint event. It supplies no additional state/identity facts.
    unknown = {"knowledge": "unknown"}
    return (key.startswith(role + ": ") and not row.get("details")
            and not row.get("known_moves") and not row.get("stat_stages")
            and all(row.get(k) == unknown for k in (
                "current_hp", "max_hp", "hp_fraction", "fainted", "condition",
                "known_item", "current_ability", "status_counter")))


def own_player_records(observation):
    own = observation["state"]["self_side"]
    roster = observation["own_request"].get("side", {}).get("pokemon", [])
    role = "p1" if observation["side"] == "self" else "p2"
    if not roster:
        rows = own["pokemon"]
        result = []
        for key, row in rows.items():
            if _empty_unpositioned_reference(key, row, role):
                positioned = [k for k in rows if k.startswith(role + "a: ")
                              and k.split(": ", 1)[1] == key.split(": ", 1)[1]]
                if len(positioned) == 1:
                    continue
            result.append((key, row))
        # Populated ambiguous records still fail closed in the encoder.
        return sorted(result)
    latest, active_public = {}, None
    for line in observation["public_history"]:
        p = line.split("|")
        if len(p) > 2 and p[2].startswith(role) and ": " in p[2]:
            latest[p[2].split(": ", 1)[1]] = p[2]
            if p[1] in {"switch", "drag", "replace"}:
                active_public = p[2]
    result, names = [], set()
    for pokemon in roster:
        ident = pokemon["ident"]
        name = ident.split(": ", 1)[-1]
        if name in names:
            raise ValueError("ambiguous_authoritative_own_request_identity")
        names.add(name)
        candidates = [(k, row) for k, row in own["pokemon"].items() if k.split(": ", 1)[-1] == name]
        selected = next((row for k, row in candidates if k == latest.get(name)), None)
        if selected is None:
            if len(candidates) != 1:
                raise ValueError("unresolved_own_public_alias_without_event_authority")
            selected = candidates[0][1]
        row = deepcopy(selected)
        # Own active identity is explicitly known even under its own Illusion.
        if pokemon.get("active") and active_public in own["pokemon"]:
            public_active = own["pokemon"][active_public]
            row["stat_stages"] = deepcopy(public_active.get("stat_stages", {}))
            if active_public.split(": ", 1)[-1] == name:
                row["details"] = public_active["details"]
            else:
                row["details"] = pokemon["details"]  # own registered identity, not opponent knowledge
        if not pokemon.get("active") or not row.get("details"):
            row["details"] = pokemon["details"]
        row.update(identity=ident, request_details=pokemon["details"],
                   own_request_active=bool(pokemon.get("active")))
        _condition(row, pokemon["condition"], own=True)
        if isinstance(pokemon.get("item"), str):
            row["known_item"] = identifier(pokemon["item"]) or None
        if isinstance(pokemon.get("ability"), str) and pokemon["ability"]:
            row["current_ability"] = identifier(pokemon["ability"])
        if "moves" in pokemon:
            row["known_moves"] = list(pokemon["moves"])
        result.append((ident, row))
    return sorted(result)
