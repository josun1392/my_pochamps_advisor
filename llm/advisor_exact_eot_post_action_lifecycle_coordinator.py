"""Detached exact post-action lifecycle coordinator."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_exact_immediate_pair_to_eot_phase_input import materialize_exact_immediate_pair_to_eot_phase_input
from llm.advisor_end_of_turn_residual_phase import materialize_end_of_turn_residual_phase
from llm.advisor_detached_end_of_turn_post_action_branch_authority import materialize_detached_end_of_turn_post_action_branch_authority
from llm.advisor_post_eot_replacement_transition import freeze_post_eot_transition
from llm.advisor_transition_preview import fingerprint_transition_preview_state

SCHEMA_VERSION = "exact-eot-post-action-lifecycle-coordinator-v1"

def coordinate_exact_eot_post_action_lifecycle(*, terminal_ledger: Mapping[str, Any], terminal_leaf_id: str, terminal_active_authorities: Mapping[str, Any], team_authorities: Mapping[str, Any], weather_authority: Mapping[str, Any] | None = None, leech_seed_transfers: tuple[Mapping[str, Any], ...] = (), switch_hazard_authorities: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Advance one exact pair leaf to the existing post-EOT decision boundary."""
    phase = materialize_exact_immediate_pair_to_eot_phase_input(terminal_ledger=terminal_ledger, terminal_leaf_id=terminal_leaf_id, terminal_active_authorities=terminal_active_authorities, weather_authority=weather_authority, leech_seed_transfers=leech_seed_transfers, switch_hazard_authorities=switch_hazard_authorities)
    if phase.get("status") != "resolved": return _result(phase.get("status", "rejected"), phase.get("reason", "exact_eot_phase_input_unavailable"), phase_input=phase)
    eot = materialize_end_of_turn_residual_phase(phase_input=phase)
    if eot.get("status") != "evaluable": return _result(eot.get("status", "rejected"), eot.get("reason", "exact_eot_unavailable"), phase_input=phase, eot_ledger=eot)
    eot_fingerprint = fingerprint_transition_preview_state(eot)
    if not isinstance(eot_fingerprint, str): return _result("rejected", "exact_eot_fingerprint_invalid", phase_input=phase, eot_ledger=eot)
    branch = materialize_detached_end_of_turn_post_action_branch_authority(eot_ledger=eot, source_eot_fingerprint=eot_fingerprint)
    if branch.get("status") != "known": return _result(branch.get("status", "rejected"), branch.get("reason", "post_eot_branch_unavailable"), phase_input=phase, eot_ledger=eot, post_eot_branch_authority=branch)
    transition = freeze_post_eot_transition(eot_ledger=eot, source_eot_fingerprint=eot_fingerprint, branch_authority=branch, team_authorities=team_authorities)
    return {"status": transition.get("status", "rejected"), "schema_version": SCHEMA_VERSION, "source_pair_terminal": {"pair_id": phase["pair_id"], "terminal_leaf_id": terminal_leaf_id, "session_id": phase["session_id"]}, "eot_phase_input": deepcopy(phase), "eot_ledger": deepcopy(eot), "eot_ledger_fingerprint": eot_fingerprint, "post_eot_branch_authority": deepcopy(branch), "post_eot_transition": deepcopy(transition), **({"detached_next_decision_state": deepcopy(transition["detached_next_decision_state"]), "next_decision_fingerprint": transition["next_decision_fingerprint"]} if transition.get("status") == "next_decision_ready" else {}), "provenance": "strict_exact_pair_to_eot_to_post_eot_transition_v1"}

def _result(status: str, reason: str, **stages: Any) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason, **deepcopy(stages)}
