"""Typed typeless physical confusion self-hit, deliberately separate from a move."""
from copy import deepcopy
from typing import Mapping
from llm.advisor_battle_state_context import calculate_stage_adjusted_stat

SCHEMA="champions-confusion-self-hit-v1"
def materialize_confusion_self_hit(*, runtime_snapshot, actor, gate, branch):
    raw=runtime_snapshot["state"][f"{actor['side']}_side"]["pokemon"][actor["slot_index"]]
    try:
        stats=raw["current_final_stats"]; attack=calculate_stage_adjusted_stat(stats["attack"]["value"],raw["stat_stages"]["attack"]); defense=calculate_stage_adjusted_stat(stats["defense"]["value"],raw["stat_stages"]["defense"]); level=raw["current_level"]
        if not isinstance(level,int) or level<1 or raw.get("current_hp") is None: raise ValueError()
        base=((((2*level)//5+2)*40*attack)//defense)//50+2
        rolls=tuple((base*factor)//100 for factor in range(85,101)); hp=raw["current_hp"]
    except (KeyError,TypeError,ValueError,ZeroDivisionError): return {"status":"incomplete","reason":"confusion_self_hit_exact_stats_unavailable"}
    disguise=raw.get("disguise_state")
    is_mimikyu=raw.get("species_id") in {"mimikyu","mimikyu-busted"} or raw.get("pokemon_id") in {"mimikyu","mimikyu-busted"}
    if disguise not in {None,"intact","broken"}: return {"status":"incomplete","reason":"confusion_disguise_state_unknown"}
    rows=[]
    for index,damage in enumerate(rolls):
        broken=is_mimikyu and disguise=="intact"; applied=0 if broken else min(hp,damage); after=hp-applied
        rows.append({"roll_index":index,"damage":applied,"raw_damage":damage,"hp_before":hp,"hp_after":after,"self_fainted":after==0,"disguise":{"status":"broken" if broken else "not_applicable" if not is_mimikyu else "already_broken","before":disguise,"after":"broken" if broken else disguise}})
    return {"status":"resolved","schema_version":SCHEMA,"actor":deepcopy(actor),"target":deepcopy(actor),"event":"confusion_self_hit","base_power":40,"type":"typeless","category":"physical","critical":False,"stab":False,"contact":False,"selected_move_does_not_execute":True,"attack_stat":attack,"defense_stat":defense,"damage_rolls":tuple(rows),"gate":deepcopy(gate),"branch":deepcopy(branch),"provenance":"canonical_confusion_self_hit_v1"}
