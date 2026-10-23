"""Opt-in public conditional two-round exchange; never native outcome truth.

No simulator handle, hidden set, opponent request or RNG enters this owner.
Damage endpoints are reused conditional references, not actual damage/KO bounds.
"""
from collections import Counter
from copy import deepcopy
from functools import lru_cache
from itertools import product
from pathlib import Path
import hashlib
import math
from time import perf_counter

from advisor.learned_baselines import VisibleBaseline
from advisor.learned_encoder import identifier, fingerprint

VERSION = "public_tactical_exchange_v1"
FORBIDDEN = {"teams", "scenario", "native_state", "opponent_request", "checkpoint",
             "seed", "future_seed", "auxiliary_labels", "coordinator_v5_supervision", "input_log"}
RECOVERY = frozenset(("recover", "softboiled", "slackoff", "milkdrink"))


def exchange_utility(profile, foe_hp, outgoing, incoming, order):
    """Two own decisions, fixed conditional hit endpoints, no probability claim.

    Terminal depletion is +/-1. Otherwise HP balance is bounded below terminal
    utility. Switching spends turn one; recovery spends turn one then attacks.
    No claim to model residuals, secondary effects, future legality or optimality.
    """
    hp = profile["hp"]
    for turn in range(2):
        def own_action():
            nonlocal hp, foe_hp
            if turn == 0 and profile["kind"] == "switch":
                return
            if turn == 0 and profile["kind"] == "recovery":
                hp = min(1., hp + profile["heal"])
            else:
                foe_hp -= outgoing
        if turn == 0 and profile["kind"] == "switch":
            hp -= incoming
        elif order == "own_first":
            own_action()
            if foe_hp <= 0:
                return 1.
            hp -= incoming
        elif order == "foe_first":
            hp -= incoming
            if hp <= 0:
                return -1.
            own_action()
        else:
            raise ValueError("unknown_exchange_order")
        if hp <= 0:
            return -1.
        if foe_hp <= 0:
            return 1.
    return max(-.95, min(.95, hp - foe_hp))


def rank_exchanges(profiles, foe_hp, baseline):
    if not profiles or not math.isfinite(foe_hp) or not 0 < foe_hp <= 1:
        raise ValueError("missing_exchange_profiles")
    rows = []
    for action, hypotheses in sorted(profiles.items()):
        scores = []
        for p in hypotheses:
            if (p["kind"] not in ("attack", "switch", "recovery") or not p["orders"]
                    or any(not math.isfinite(x) or x < 0 for x in
                           (*p["outgoing"], *p["incoming"], p["hp"], p["heal"]))):
                raise ValueError("invalid_exchange_reference")
            scores += [exchange_utility(p, foe_hp, out, inc, order)
                       for out, inc, order in product(p["outgoing"], p["incoming"], p["orders"])]
        if not scores:
            raise ValueError("missing_exchange_hypotheses")
        rows.append({"action": action, "kind": hypotheses[0]["kind"],
                     "worst_utility": min(scores), "mean_scenario_utility": sum(scores)/len(scores),
                     "scenario_count": len(scores), "conditional_hypotheses": hypotheses})
    best = max(rows, key=lambda r: (r["worst_utility"], r["mean_scenario_utility"],
                                   r["action"] == baseline, -r["action"]))
    return best["action"], rows


@lru_cache(maxsize=2)
def public_reference_owner(catalog):
    from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder
    from advisor.learned_combat_v5_strategic import priors
    return StrategicPublicCategoricalEncoder(catalog), priors()[0]["native_moves"]


@lru_cache(maxsize=2)
def public_exchange_metadata(checkout):
    import json
    import subprocess
    from advisor.showdown_bridge import SHOWDOWN_COMMIT, FORMAT_ID
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
    if actual != SHOWDOWN_COMMIT:
        raise ValueError("public_tactical_native_pin_mismatch")
    bridge = Path(__file__).resolve().parents[1]/"tools/showdown_bridge/public-exchange-metadata.cjs"
    raw = subprocess.check_output(["node", str(bridge), checkout], text=True)
    data = json.loads(raw)
    if data.get("schema_version") != "pinned-public-exchange-metadata-v1" or data.get("format_id") != FORMAT_ID:
        raise ValueError("public_tactical_metadata_contract_mismatch")
    return data


def own_fraction(pokemon):
    parts = pokemon.get("condition", "").split()[0:1]
    health = parts[0].split("/") if parts else []
    if len(health) != 2 or not all(x.isdigit() for x in health):
        return None
    current, maximum = map(int, health)
    return current/maximum if 0 < current <= maximum else None


def response_hypotheses(revealed, legal_moves, native_moves, exchange_metadata, counts, global_counts):
    """Bounded public possibilities, not a revealed set or calibrated belief.

    Canonically legal individual move support gates all unrevealed hypotheses.
    Existing train-only species marginal frequencies prioritize possibilities.
    A revealed runtime move need not have been selectable on the starting form.
    """
    def supported(m):
        return native_moves.get(m,{}).get("referenceSupported") and exchange_metadata.get(m,{}).get("simpleExchange")
    seen=sorted({identifier(m)for m in revealed if supported(identifier(m))},
                key=lambda m:(-native_moves[m]["power"],m))[:3]
    possible=sorted({identifier(m)for m in legal_moves if supported(identifier(m)) and identifier(m)not in seen},
        key=lambda m:(-counts.get(m,0),-global_counts.get(m,0),-native_moves[m]["power"],m))
    return [{"move":m,"basis":"public_revealed","currently_selectable":"unknown"}for m in seen]+[
        {"move":m,"basis":"legal_species_train_marginal_hypothesis","currently_selectable":"unknown",
         "species_training_set_count":counts.get(m,0)}for m in possible[:3-len(seen)]]


class PublicTacticalOpponent:
    kind = VERSION

    def __init__(self, seed=0, *, catalog=None, checkout):
        catalog = catalog or Path(__file__).resolve().parents[1]/"models/showdown_mc_domain_v1/catalog.json"
        self.reference, self.native_moves = public_reference_owner(str(catalog))
        self.exchange_metadata = public_exchange_metadata(str(checkout))["moves"]
        self.base = VisibleBaseline("tactical_heuristic", seed)
        self.model_id = VERSION + ":" + fingerprint({"source":hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "catalog":self.reference.catalog_fingerprint,"native_metadata":self.exchange_metadata,"native_moves":self.native_moves})
        self.counts, self.last_decision, self._last_key = Counter(), None, None

    def _profiles(self, view, baseline):
        from advisor.learned_combat_v5 import active_public
        from advisor.learned_combat_v5_strategic import public_species_candidates,priors
        from advisor.learned_combat_v5 import inventory
        from advisor.learned_combat_v5_references import reference_features
        from advisor.learned_tactics_encoder import public_side_conditions
        from advisor.learned_own_identity import own_player_records

        notes = {"basis": "public_legal_move_hypotheses_conditional_reference_endpoints_two_rounds",
                 "unknown_modifiers": "neutral_reference_not_claimed_absent",
                 "opponent_future_move_legality": "unknown_no_opponent_request_access",
                 "future_own_move_legality": "conditional_not_a_native_mask_prediction",
                 "omitted": ["critical", "miss", "secondary_effect", "residual", "opponent_switch", "unselected_legal_move_possibilities"],
                 "probability_scope": "no_probability_assigned_to_hypotheses"}
        if view.get("request_state") != "move":
            return {}, 0., {**notes, "reason": "administrative_or_forced_request"}
        own_player_records(view)  # established owner binding, including own bench
        foe = active_public(view)
        hp = foe.get("hp_fraction")
        if not isinstance(hp, (float, int)) or not 0 < hp <= 1:
            return {}, 0., {**notes, "reason": "unknown_opponent_public_hp"}
        projection = self.reference.project(view)
        if len(public_species_candidates(view)) != 1 or projection["unsupported"]:
            return {}, hp, {**notes, "reason": "ambiguous_appearance_or_public_projection"}
        if any(v is True for p in projection["active"] for v in p["effects"].values()):
            return {}, hp, {**notes, "reason": "unsupported_active_volatile"}
        if foe.get("condition") in ("slp", "frz") or isinstance(projection["weather"], dict) or projection["weather"] in ("sandstorm", "hail"):
            return {}, hp, {**notes, "reason": "unsupported_status_or_residual_weather"}
        simple = lambda mid: self.exchange_metadata.get(identifier(mid), {}).get("simpleExchange") is True
        species=public_species_candidates(view)[0];entry=inventory()["species"][species];data,_=priors()
        prior=data["species"].get(identifier(entry["start_species"]),{})
        hypotheses=response_hypotheses(foe.get("known_moves",[]),entry["moves"],self.native_moves,
            self.exchange_metadata,prior.get("moves",{}),data["global_counts"]["moves"])
        if not hypotheses:
            return {}, hp, {**notes, "reason": "no_supported_public_legal_attack_hypothesis"}
        roster = view["own_request"].get("side", {}).get("pokemon", [])
        active = next((p for p in roster if p.get("active")), None)
        moves = view["own_request"].get("active", [{}])[0].get("moves", [])
        hazard_entry = any(public_side_conditions(view)[:4])
        notes.update(opponent_move_hypotheses=hypotheses, switch_entry_unavailable=hazard_entry)
        profiles = {}
        for move_hypothesis in hypotheses:
            mid=move_hypothesis["move"]
            # Retain the real known_moves list. A conditional mechanics call
            # has a separate explicitly hypothetical argument; no revelation is
            # fabricated, cached or passed into the Foundation policy.
            hypothesis = deepcopy(view)
            for pokemon in hypothesis["own_request"].get("side", {}).get("pokemon", []):
                pokemon["moves"] = [m for m in pokemon.get("moves", []) if simple(m)]
            refs, _ = reference_features(hypothesis, self.reference, self.native_moves,incoming_move_hypotheses=(mid,))
            attacks = [a for a in range(6, 10) if view["action_mask"][a] and a-6<len(moves)
                       and simple(moves[a-6]["id"]) and refs[a, 2] and not refs[a, 22]]
            future = max((tuple(float(v) for v in refs[a, :2]) for a in attacks), default=None)
            for a, legal in enumerate(view["action_mask"]):
                if not legal or a == 26 or a >= 10 or refs[a, 22] or not refs[a, 18]:
                    continue
                switch = a < 6
                p = roster[a] if switch and a < len(roster) else active
                health = own_fraction(p) if p else None
                if health is None or switch and hazard_entry:
                    continue
                heal = 0.
                if switch:
                    kind = "switch"
                    out = tuple(float(v) for v in refs[a, :2]) if refs[a, 2] else None
                elif a in attacks:
                    kind, out = "attack", tuple(float(v) for v in refs[a, :2])
                elif a-6 < len(moves) and identifier(moves[a-6]["id"]) in RECOVERY and future:
                    kind, out, heal = "recovery", future, .5
                else:
                    continue
                if out is None:
                    continue
                # Unknown ability/item/speed interactions preserve BOTH orders.
                # A restricted known-modifier reference can narrow conditional
                # order; this remains an estimate, never native order authority.
                orders = ("own_first", "foe_first")
                if kind == "attack" and not refs[a, 21] and refs[a, 12]:
                    priority = self.native_moves.get(identifier(moves[a-6]["id"]), {}).get("priority", 0)
                    relation = priority-self.native_moves[mid]["priority"]
                    if relation or refs[a, 13]:
                        orders = ("own_first",) if (relation or refs[a, 13]) > 0 else ("foe_first",)
                profiles.setdefault(a, []).append({"action": a, "kind": kind, "hp": health,
                    "outgoing": out, "incoming": tuple(float(v) for v in refs[a, 16:18]),
                    "heal": heal, "orders": orders, "opponent_move_hypothesis": move_hypothesis,
                    "unknown_hidden_modifiers": bool(refs[a, 21]), "conditional_speed_relation": float(refs[a, 13]),
                    "nominal_move_priority": float(refs[a, 14]*7)})
        # Each compared action must face the same revealed hypothesis set.
        profiles = {a: rows for a, rows in profiles.items() if len(rows) == len(hypotheses)}
        return profiles, hp, notes

    def act(self, view):
        if FORBIDDEN & set(view):
            raise ValueError("privileged_public_tactical_input")
        allowed = [i for i, v in enumerate(view["action_mask"]) if v]
        if not allowed:
            raise ValueError("no_public_legal_action")
        if allowed == [26]:
            self.last_decision = {"action": 26, "fallback": "administrative_wait"}
            return 26
        key = fingerprint(view)
        if key == self._last_key:
            return self.last_decision["action"]
        started = perf_counter()
        baseline = self.base.act(view)
        if baseline not in allowed:
            raise ValueError("public_tactical_baseline_mask_violation")
        profiles, hp, notes = self._profiles(view, baseline)
        profiles = {a: p for a,p in profiles.items() if a in allowed}
        action, rows, fallback = baseline, [], None
        if baseline not in profiles:
            fallback = "no_comparable_baseline_profile"
        elif len(profiles) < 2:
            fallback = "no_comparable_alternative"
        else:
            action, rows = rank_exchanges(profiles, hp, baseline)
        assert action in allowed
        self.last_decision = {"version": VERSION, "action": action, "baseline_action": baseline,
            "disagrees": action != baseline, "fallback": fallback, "rationale": notes,
            "comparisons": rows, "legal_actions": allowed, "seconds": perf_counter()-started}
        self.counts["public_decisions"] += 1
        self.counts["comparable_decisions"] += not bool(fallback)
        self.counts["disagreements"] += action != baseline
        self.counts["fallback:"+str(notes.get("reason", fallback))] += bool(fallback)
        self._last_key = key
        return action

    def drain_counts(self):
        result = dict(self.counts)
        self.counts.clear()
        return result
