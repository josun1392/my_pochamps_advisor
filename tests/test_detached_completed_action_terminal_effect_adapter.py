import pytest
from llm.advisor_detached_completed_action_terminal_effect_adapter import attach_detached_completed_action_terminal_effect as attach

R={"side":"self","pokemon_id":"r"}; D={"side":"opponent","pokemon_id":"d"}
def state(): return {"status":"resolved","first_action":{"candidate_id":"a","move_id":"tackle"},"active":{"self":{"owner":R},"opponent":{"owner":D}}}
def source(family="ordinary_single_hit",terminal=True,reason="normal_completion"): return {"family":family,"terminal":terminal,"terminal_id":"t:1","action_id":"a","move_id":"tackle","actor":D,"target":R,"terminal_reason":reason}
def authority(): return {"status":"resolved","outcome":"transferred","trigger_direction":"pickpocket_defender_contact","receiver":R,"donor":D,"item":"orb","receiver_item_before":{"status":"known_absent","value":None},"donor_item_before":{"status":"known","value":"orb"},"receiver_item_after":{"status":"known","value":"orb"},"donor_item_after":{"status":"known_absent","value":None}}

@pytest.mark.parametrize("family",["ordinary_single_hit","fixed_two_hit","variable_two_to_five_hit","population_bomb","triple_axel","triple_kick"])
def test_all_supported_terminal_families_preserve_identity(family):
 got=attach(terminal_source=source(family),detached_state=state(),effect_kind="ability_item_steal",effect_authority=authority(),sheer_force={"status":"resolved","action_id":"a","move_id":"tackle"})
 assert got["result"]=="applied" and got["terminal_source"]["family"]==family and got["terminal_source"]["terminal_id"]=="t:1"

def test_nonterminal_and_foreign_evidence_fail_closed():
 assert attach(terminal_source=source(terminal=False),detached_state=state(),effect_kind="ability_item_steal",effect_authority=authority())["status"]=="rejected"
 assert attach(terminal_source={**source(),"action_id":"foreign"},detached_state=state(),effect_kind="ability_item_steal",effect_authority=authority())["status"]=="rejected"

@pytest.mark.parametrize("reason",["miss","target_fainted","attacker_fainted_from_contact_reactive_damage","normal_completion"])
def test_early_terminal_reason_and_incomplete_sheer_force_are_preserved(reason):
 got=attach(terminal_source=source(reason=reason),detached_state=state(),effect_kind="ability_item_steal",effect_authority=authority(),sheer_force={"status":"resolved","action_id":"a","move_id":"tackle"})
 assert got["terminal_source"]["terminal_reason"]==reason
 assert attach(terminal_source=source(),detached_state=state(),effect_kind="ability_item_steal",effect_authority=authority(),sheer_force={"status":"incomplete"})["status"]=="incomplete"


def test_adapter_applies_atomic_item_projection_without_mutating_input():
 before=state()
 got=attach(terminal_source=source(),detached_state=before,effect_kind="ability_item_steal",effect_authority=authority())
 assert got["detached_state_after"]["active"]["self"]["hypothetical_item"]=={"status":"known","value":"orb"}
 assert got["detached_state_after"]["active"]["opponent"]["hypothetical_item"]=={"status":"known_absent","value":None}
 assert before==state()
 forged=authority();forged["donor_item_after"]={"status":"known","value":"orb"}
 assert attach(terminal_source=source(),detached_state=before,effect_kind="ability_item_steal",effect_authority=forged)["status"]=="rejected"
