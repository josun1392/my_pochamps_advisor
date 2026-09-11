from llm.advisor_exact_eot_post_action_lifecycle_coordinator import coordinate_exact_eot_post_action_lifecycle
from llm.advisor_exact_immediate_pair_to_eot_phase_input import materialize_exact_immediate_pair_to_eot_phase_input
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_post_eot_replacement_transition import post_eot_source_binding
from tests.test_end_of_turn_residual_phase import _ledger, _owner, _row
from tests.test_exact_immediate_pair_to_eot_phase_input import _authorities

def _teams(ledger, *, bench=False):
    binding = post_eot_source_binding(ledger); rows = {}
    for side in ("self", "opponent"):
        final = ledger["post_end_of_turn_active_states"][side]; owner=final["owner"]
        members=[{"owner": owner, "hp":{"status":"known","current_hp":final["current_hp"],"maximum_hp":final["maximum_hp"]}, "eligible":{"status":"known","value":True}}]
        if bench and side == "self": members.append({"owner":{**_owner("self","bench"),"slot_index":1},"hp":{"status":"known","current_hp":50,"maximum_hp":100},"eligible":{"status":"known","value":True}})
        rows[side]={"status":"known","completeness":"complete","side":side,"source_binding":binding,"members":members}
    return rows

def _prepare(*, self_hp=50, self_row=None):
    authorities=_authorities(self_hp=self_hp,self_row=self_row)
    phase=materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=_ledger(self_hp=self_hp),terminal_leaf_id="leaf",terminal_active_authorities=authorities)
    eot=materialize_end_of_turn_residual_phase(phase_input=phase)
    return authorities,eot

def test_surviving_leaf_reaches_existing_next_decision_boundary():
    authorities,eot=_prepare()
    result=coordinate_exact_eot_post_action_lifecycle(terminal_ledger=_ledger(),terminal_leaf_id="leaf",terminal_active_authorities=authorities,team_authorities=_teams(eot))
    assert result["status"]=="next_decision_ready" and result["next_decision_fingerprint"]
    assert result["post_eot_transition"]["status"]=="next_decision_ready"

def test_residual_ko_exposes_existing_replacement_or_battle_terminal_result():
    row=_row("self","a",6,condition="burn"); authorities,eot=_prepare(self_hp=6,self_row=row)
    result=coordinate_exact_eot_post_action_lifecycle(terminal_ledger=_ledger(self_hp=6),terminal_leaf_id="leaf",terminal_active_authorities=authorities,team_authorities=_teams(eot,bench=True))
    assert result["status"]=="replacement_required" and result["post_eot_transition"]["requirements"]["self"]["candidates"]==({**_owner("self","bench"),"slot_index":1},)
    terminal=coordinate_exact_eot_post_action_lifecycle(terminal_ledger=_ledger(self_hp=6),terminal_leaf_id="leaf",terminal_active_authorities=authorities,team_authorities=_teams(eot))
    assert terminal["status"]=="battle_terminal" and "detached_next_decision_state" not in terminal

def test_invalid_terminal_or_foreign_team_fails_closed():
    authorities,eot=_prepare(); teams=_teams(eot); teams["self"]["source_binding"]["pair_id"]="foreign"
    assert coordinate_exact_eot_post_action_lifecycle(terminal_ledger=_ledger(),terminal_leaf_id="leaf",terminal_active_authorities=authorities,team_authorities=teams)["status"]=="rejected"
    assert coordinate_exact_eot_post_action_lifecycle(terminal_ledger=_ledger(),terminal_leaf_id="foreign",terminal_active_authorities=authorities,team_authorities=_teams(eot))["status"]=="rejected"
