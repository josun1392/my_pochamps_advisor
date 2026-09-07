"""Exact, detached Champions confusion current-action gate."""
from copy import deepcopy
from fractions import Fraction
from typing import Mapping
from llm.advisor_champions_sleep_freeze_action_gate import fd, fraction
from llm.advisor_champions_confusion_progression import valid_confusion_progression

SCHEMA = "champions-confusion-action-gate-v1"

def _branch(kind, probability, confusion, progression, **extra):
    return {"kind": kind, "executes": kind in {"executes", "confusion_selected_action_executes", "confusion_snaps_out_and_executes"}, "probability": fd(probability), "confusion_after": confusion, "progression_after": deepcopy(progression), **extra}

def resolve_confusion_branches(*, progression, ability):
    if ability.get("status") != "resolved": return {"status": "incomplete", "reason": "confusion_ability_applicability_unknown"}
    if ability.get("own_tempo_active"):
        return {"status": "rejected", "reason": "active_own_tempo_cannot_retain_confusion"}
    prior = progression["prior_opportunities"]
    chosen = progression.get("duration")
    options = [(chosen, Fraction(1))] if chosen is not None else [(2, Fraction(1,4)), (3, Fraction(1,4)), (4, Fraction(1,4)), (5, Fraction(1,4))]
    options = [(duration, weight) for duration, weight in options if duration > prior]
    if not options: return {"status": "rejected", "reason": "confusion_progression_past_duration"}
    mass = sum((weight for _, weight in options), Fraction())
    rows=[]
    for duration, weight in options:
        opportunity = prior + 1
        identity = f"{progression['origin_id']}:duration:{duration}"
        if opportunity >= duration:
            rows.append(_branch("confusion_snaps_out_and_executes", weight / mass, "none", None, opportunity=opportunity, duration=duration, duration_identity=identity))
            continue
        after = {**deepcopy(progression), "prior_opportunities": opportunity, "duration": duration}
        rows.extend((_branch("confusion_self_hit", weight / mass * Fraction(1,3), "confused", after, opportunity=opportunity, duration=duration, duration_identity=identity),
                     _branch("confusion_selected_action_executes", weight / mass * Fraction(2,3), "confused", after, opportunity=opportunity, duration=duration, duration_identity=identity)))
    return rows

def freeze_champions_confusion_action_gate(*, strategy_d0, runtime_snapshot, actor, action_id, move_id, action_order, path=()):
    from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness
    if runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot).get("status") != "current": return {"status":"rejected","reason":"stale_champions_confusion_gate_d0"}
    if actor not in strategy_d0.get("active_owners", {}).values() or not isinstance(action_id,str) or not action_id: return {"status":"rejected","reason":"champions_confusion_gate_actor_action_invalid"}
    raw=runtime_snapshot["state"][f"{actor['side']}_side"]["pokemon"][actor["slot_index"]]
    state=raw.get("current_confusion")
    # Older runtime snapshots predate this volatile field; absence denotes the
    # canonical inactive default, while an explicit unknown remains fail-closed.
    if state == "unknown": return {"status":"incomplete","reason":"champions_confusion_current_state_unknown"}
    if state is None: state = "none"
    if state == "none": return {"status":"resolved","schema_version":SCHEMA,"session_id":strategy_d0["session_id"],"source_runtime_fingerprint":strategy_d0["source_runtime_fingerprint"],"source_branch_fingerprint":strategy_d0["strategy_preview_fingerprint"],"actor":deepcopy(actor),"action_id":action_id,"move_id":move_id,"confusion":"none","progression":None,"ability_authority":None,"action_order":deepcopy(action_order),"path":tuple(path),"branches":(_branch("executes",Fraction(1),"none",None),),"root_probability_mass":fd(Fraction(1)),"provenance":"champions_confusion_gate_v1"}
    progression=raw.get("champions_confusion_progression")
    if state != "confused" or not valid_confusion_progression(progression,actor) or progression.get("confusion_observation") != raw.get("confusion_provenance"): return {"status":"incomplete","reason":"champions_confusion_progression_missing_or_stale"}
    abilities={side:runtime_snapshot["state"][f"{side}_side"]["pokemon"][owner["slot_index"]].get("current_ability") for side,owner in strategy_d0["active_owners"].items()}
    exact=all(isinstance(value,str) and value for value in abilities.values()); gas="neutralizing-gas" in abilities.values()
    ability={"status":"resolved" if exact else "incomplete","holder":deepcopy(actor),"abilities":deepcopy(abilities),"ability_id":abilities.get(actor["side"]),"suppressed":gas,"own_tempo_active":exact and abilities.get(actor["side"])=="own-tempo" and not gas}
    branches=resolve_confusion_branches(progression=progression,ability=ability)
    if isinstance(branches,Mapping): return dict(branches)
    for index,row in enumerate(branches): row["branch_id"]=f"{action_id}:confusion:{index}:{row['kind']}"
    return {"status":"resolved","schema_version":SCHEMA,"session_id":strategy_d0["session_id"],"source_runtime_fingerprint":strategy_d0["source_runtime_fingerprint"],"source_branch_fingerprint":strategy_d0["strategy_preview_fingerprint"],"actor":deepcopy(actor),"action_id":action_id,"move_id":move_id,"confusion":"confused","progression":deepcopy(progression),"ability_authority":ability,"action_order":deepcopy(action_order),"path":tuple(path),"branches":tuple(branches),"root_probability_mass":fd(Fraction(1)),"provenance":"champions_confusion_gate_v1"}

def validate_confusion_gate(authority):
    try:
        if authority.get("status")!="resolved" or authority.get("schema_version")!=SCHEMA: return False
        if authority["confusion"]=="none": return authority["branches"]==(_branch("executes",Fraction(1),"none",None),)
        if not valid_confusion_progression(authority["progression"],authority["actor"]): return False
        ability=authority["ability_authority"]; abilities=ability["abilities"]
        if ability["status"] != ("resolved" if all(isinstance(v,str) and v for v in abilities.values()) else "incomplete") or ability["suppressed"] != ("neutralizing-gas" in abilities.values()) or ability["own_tempo_active"] != (ability["status"]=="resolved" and ability["ability_id"]=="own-tempo" and not ability["suppressed"]): return False
        expected=resolve_confusion_branches(progression=authority["progression"],ability=ability)
        if isinstance(expected,Mapping): return False
        for i,row in enumerate(expected): row["branch_id"]=f"{authority['action_id']}:confusion:{i}:{row['kind']}"
        return tuple(expected)==authority["branches"] and sum((fraction(row["probability"]) for row in expected),Fraction())==1 and authority["root_probability_mass"]==fd(Fraction(1))
    except (KeyError,TypeError,ValueError): return False

def materialize_confusion_branch(*, strategy_d0, runtime_snapshot, authority, branch):
    from llm.advisor_reducer_state_model import state_fingerprint
    from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
    if not validate_confusion_gate(authority) or branch not in authority["branches"]: return {"status":"rejected","reason":"invalid_champions_confusion_branch"}
    if freeze_champions_confusion_action_gate(strategy_d0=strategy_d0,runtime_snapshot=runtime_snapshot,actor=authority["actor"],action_id=authority["action_id"],move_id=authority["move_id"],action_order=authority["action_order"],path=authority["path"]) != authority: return {"status":"rejected","reason":"foreign_champions_confusion_branch"}
    state=deepcopy(runtime_snapshot["state"]); raw=state[f"{authority['actor']['side']}_side"]["pokemon"][authority["actor"]["slot_index"]]
    raw["current_confusion"]=branch["confusion_after"]; raw["champions_confusion_progression"]=deepcopy(branch["progression_after"])
    if branch["confusion_after"]=="none": raw["confusion_provenance"]={**deepcopy(raw.get("confusion_provenance", {})),"state":"none","hypothetical_provenance":"champions_confusion_snap_out_v1"}
    raw["detached_champions_confusion_view"]=True
    snapshot={"status":"runtime_snapshot_ready","session_id":state["session_id"],"state":state,"state_fingerprint":state_fingerprint(state)}
    return {"status":"resolved","strategy_d0":freeze_runtime_strategy_d0(runtime_snapshot=snapshot,decision_owner=authority["actor"]),"runtime_snapshot":snapshot,"authority":deepcopy(authority),"branch":deepcopy(branch),"provenance":"detached_champions_confusion_branch_v1"}
