from llm.advisor_opponent_action_evaluator import evaluate_opponent_action_candidates


def _stats():
 return {"hp":100,"attack":100,"defense":100,"special-attack":100,"special-defense":100,"speed":100}


def _side(identity, side, types):
 return {"pokemon_identity":identity,"side":side,"types":{"available":True,"value":types},"type_authority":{"status":"known","basis":"current_type_context"},"base_stats":{"available":True,"value":_stats()},"final_stats":{"available":True,"value":_stats()}}


def _candidate(category="physical", hp=100):
 current={"trusted_level_context":{"current_levels":[{"side":"opponent","value":50,"provenance":{"pokemon_id":"garchomp","slot_index":1}}]},"current_hp_context":{"current_hp":[{"side":"self","current_hp":hp,"maximum_hp":100,"status":"user_confirmed","source":"user_confirmed_current_hp","confidence":"known"}]}}
 metadata={"move_id":"tackle","category":category,"power":40,"type":"normal","priority":0,"target":"selected-pokemon"}
 return {"candidate_id":"opponent-action:s:garchomp:tackle:0","role":"opponent_action","session_id":"s","pokemon_identity":"garchomp","move_id":"tackle","move_identity_authority":"frozen_known_move_context","metadata_supportability":"complete","move_metadata":metadata,"mechanics_snapshot":{"attacker":{"species_id":"garchomp","slot_index":1},"defender":{"species_id":"pikachu","slot_index":0},"move":{"slot_index":0,"owner_species_id":"garchomp",**metadata},"battle_context":{"current_state":current,"stat_provenance":{"attacker":_side("garchomp","opponent",["normal"]),"defender":_side("pikachu","self",["normal"])}}}}


def test_formula_incoming_q12_keeps_self_hp_ko_and_probability_candidate_local():
 evaluated=evaluate_opponent_action_candidates({"known_move_state":"partially_known","known_candidate_count":1,"unknown_slots_remaining":3,"candidate_set_complete":False,"opponent_action_candidates":[_candidate()]})
 row=evaluated["opponent_action_evaluations"][0]
 assert row["mechanical_evaluation_status"]=="complete"
 assert row["incoming_q12"]["status"]=="resolved"
 assert row["incoming_damage"]["ko_interpretation"]["ko_supportability"]=="complete"
 assert row["incoming_damage"]["ko_probability"]["ko_probability_supportability"]=="complete"
 assert evaluated["mechanical_evaluation_complete"] is True


def test_unknown_self_hp_preserves_damage_and_withholds_ko_probability():
 candidate=_candidate(); candidate["mechanics_snapshot"]["battle_context"]["current_state"]["current_hp_context"]={"current_hp":[{"side":"self","state":"unknown"}]}
 row=evaluate_opponent_action_candidates({"opponent_action_candidates":[candidate]})["opponent_action_evaluations"][0]
 assert row["incoming_damage"]["status"]=="known"
 assert row["incoming_damage"]["ko_interpretation"]["ko_supportability"]=="insufficient_context"
 assert row["incoming_damage"]["ko_probability"]["ko_probability_supportability"]=="insufficient_context"


def test_reversed_direct_formula_reuses_opponent_offense_and_self_defense():
 candidate=_candidate()
 absent={"status":"known_absent"}; side={"ability":absent,"item":absent,"boosts":{"attack":0,"defense":0,"special-attack":0,"special-defense":0,"speed":0},"current_hp":100,"max_hp":100,"status":absent}
 candidate["mechanics_snapshot"]["battle_context"]["current_state"]["direct_mechanics_context"]={"generation":"gen9","attacker":side,"defender":side,"field":{"weather":absent,"terrain":absent}}
 candidate["mechanics_snapshot"]["battle_context"]["stat_provenance"]["attacker"]["known_item"]={"available":True,"status":"known_absent","value":None}
 row=evaluate_opponent_action_candidates({"opponent_action_candidates":[candidate]})["opponent_action_evaluations"][0]
 assert row["incoming_damage"]["status"]=="known"
 assert row["incoming_damage"]["mechanics_source"]=="native_q12_direct_damage"
 assert row["incoming_damage"]["ko_interpretation"]["defender_hp_authority"]=="exact_current_hp"


def test_exact_defender_resist_berry_reaches_incoming_ko_evidence():
 def resolve(item):
  candidate=_candidate(hp=50)
  candidate["move_metadata"].update(power=100)
  candidate["mechanics_snapshot"]["move"].update(power=100)
  absent={"status":"known_absent"}; side={"ability":absent,"item":absent,"boosts":{"attack":0,"defense":0,"special-attack":0,"special-defense":0,"speed":0},"current_hp":100,"max_hp":100,"status":absent}
  side["current_hp"] = 50
  candidate["mechanics_snapshot"]["battle_context"]["current_state"]["direct_mechanics_context"]={"generation":"gen9","attacker":side,"defender":side,"field":{"weather":absent,"terrain":absent}}
  candidate["mechanics_snapshot"]["battle_context"]["stat_provenance"]["attacker"]["known_item"]={"status":"known_absent","value":None}
  candidate["mechanics_snapshot"]["battle_context"]["stat_provenance"]["defender"]["known_item"]={"status":"known_absent","value":None} if item is None else {"status":"known","value":item,"profile_source":"frozen_candidate_item_authority"}
  return evaluate_opponent_action_candidates({"opponent_action_candidates":[candidate]})["opponent_action_evaluations"][0]["incoming_damage"]

 baseline, chilan = resolve(None), resolve("chilan-berry")
 assert baseline["status"] == chilan["status"] == "known"
 assert chilan["damage_range"]["maximum"] < baseline["damage_range"]["maximum"]
 assert chilan["ko_result"]["single_hit_probability"] < baseline["ko_result"]["single_hit_probability"]
 assert chilan["applied_damage_modifiers"] == ["defender_item_chilan_berry_reduction"]
 assert chilan["ko_interpretation"]["ko_supportability"] == "complete"


def test_status_and_unsupported_metadata_remain_evaluated_identities_without_damage():
 status=_candidate("status")
 unsupported={"candidate_id":"x","metadata_supportability":"unsupported_mechanic"}
 rows=evaluate_opponent_action_candidates({"opponent_action_candidates":[status,unsupported]})["opponent_action_evaluations"]
 assert rows[0]["incoming_damage"]["status"]=="not_applicable"
 assert rows[1]["incoming_damage"]["status"]=="unsupported_mechanic"
