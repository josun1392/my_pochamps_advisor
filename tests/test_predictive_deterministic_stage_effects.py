from llm.advisor_deterministic_move_stage_effect_metadata import build_deterministic_move_stage_effect_metadata
from llm.advisor_predictive_deterministic_stage_effects import compose_predictive_deterministic_stage_effects

def _interval(move, rolls=(20,)*16, hp=100, route="target"):
 return {"completeness":"exact_complete","session_id":"s","source_branch_fingerprint":"f","move_id":move,"exact_damage_rolls":rolls,"target_hp_before":hp if route=="target" else None,"target_routing":route}
def _provenance(self_stages, target_stages):
 return {"attacker":{"stat_stages":{"available":True,"value":self_stages}},"defender":{"stat_stages":{"available":True,"value":target_stages}}}
def _authority(move, category, changes): return build_deterministic_move_stage_effect_metadata({"move_id":move,"category":category,"stat_changes":changes,"effect_chance":100})

def test_self_effects_cap_and_close_combat_are_atomic():
 flame=compose_predictive_deterministic_stage_effects(interval=_interval("flame-charge"),stage_effect_authority=_authority("flame-charge","physical",[{"stat":"speed","change":1}]),stat_provenance=_provenance({"speed":6},{"special-defense":0}))
 close=compose_predictive_deterministic_stage_effects(interval=_interval("close-combat"),stage_effect_authority=_authority("close-combat","physical",[{"stat":"defense","change":-1},{"stat":"special-defense","change":-1}]),stat_provenance=_provenance({"defense":-6,"special-defense":0},{"special-defense":0}))
 assert flame["guaranteed_effects"][0]["resulting_stage"]==6
 assert [(x["stat"],x["resulting_stage"]) for x in close["guaranteed_effects"]]==[("defense",-6),("special-defense",-1)]

def test_acid_spray_is_conditional_on_survival_and_blocked_by_substitute():
 authority=_authority("acid-spray","special",[{"stat":"special-defense","change":-2}]); provenance=_provenance({}, {"special-defense":0})
 split=compose_predictive_deterministic_stage_effects(interval=_interval("acid-spray",(80,120)*8,100),stage_effect_authority=authority,stat_provenance=provenance)
 sub=compose_predictive_deterministic_stage_effects(interval=_interval("acid-spray",route="substitute"),stage_effect_authority=authority,stat_provenance=provenance)
 assert split["conditional"] and split["branches"][0]["effects"] and not split["branches"][1]["effects"]
 assert sub["guaranteed_effects"]==()

def test_unknown_affected_stage_is_incomplete_not_neutral():
 result=compose_predictive_deterministic_stage_effects(interval=_interval("flame-charge"),stage_effect_authority=_authority("flame-charge","physical",[{"stat":"speed","change":1}]),stat_provenance=_provenance({},{}))
 assert result=={"status":"incomplete","reason":"self.speed_stage_unknown"}
