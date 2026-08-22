from copy import deepcopy

from llm.advisor_candidate_outcome_materialization import materialize_candidates
from llm.advisor_current_action_authority import freeze_current_action_authority
from llm.advisor_current_execution_authority import (
    enrich_discovered_candidates,
    freeze_current_execution_authority,
)
from llm.advisor_current_state_candidate_discovery import discover_candidates
from llm.advisor_deterministic_candidate_ranking import rank_candidates
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_executable_switch_transition import _incoming
from tests.test_forced_switch_execution import _owner, _state


def _selection(state, *, moves=("water-gun",), switches=("incoming",)):
    owner = _owner(state, "self")
    fingerprint = fingerprint_transition_preview_state(state)
    return freeze_current_action_authority(
        decision_state=state,
        decision_owner=owner,
        moves=[{"owner": owner, "source_branch_fingerprint": fingerprint, "move_id": move, "selection": "selectable"} for move in moves],
        switches=[{"owner": owner, "source_branch_fingerprint": fingerprint, "pokemon_id": switch, "selection": "selectable"} for switch in switches],
    )


def _current_incoming(state, *, pokemon_id="incoming"):
    authority = _incoming()
    authority["owner"] = {**authority["owner"], "pokemon_id": pokemon_id}
    authority["source_branch_fingerprint"] = fingerprint_transition_preview_state(state)
    return authority


def test_execution_bundle_freezes_d0_bound_switch_authority_and_is_detached():
    state, _ = _state()
    snapshot = _selection(state)
    incoming = _current_incoming(state)
    bundle = freeze_current_execution_authority(selection_snapshot=snapshot, switch_incoming=[incoming])

    assert bundle["schema_version"] == "deterministic-current-execution-authority-v1"
    assert bundle["decision_owner"] == _owner(state, "self")
    assert bundle["execution_coverage"] == {"current_predictive_execution_authority": 1, "observation_required": 1, "execution_incomplete": 0}
    incoming["hp_authority"]["current_hp"] = 1
    switch = next(record for record in bundle["records"] if record["action_id"] == "manual_switch:incoming")
    assert switch["authority"]["hp_authority"]["current_hp"] == 80


def test_historical_observation_never_upgrades_attack_and_missing_switch_is_incomplete():
    state, _ = _state()
    snapshot = _selection(state)
    historical = {"schema_version": "observed-direct-damage-result-v1", "move_id": "water-gun", "source_branch_fingerprint": fingerprint_transition_preview_state(state)}
    bundle = freeze_current_execution_authority(selection_snapshot=snapshot, switch_incoming=[])
    records = {record["action_id"]: record for record in bundle["records"]}

    assert historical["schema_version"].startswith("observed-")
    assert records["attack:water-gun"]["authority_class"] == "observation_required"
    assert records["attack:water-gun"]["authority"] is None
    assert records["manual_switch:incoming"]["reason"] == "incoming_state_unavailable"


def test_join_is_d0_bound_order_invariant_and_rejects_foreign_incoming_authority():
    state, _ = _state()
    snapshot = _selection(state, moves=("water-gun", "tackle"), switches=("incoming", "bench-b"))
    incoming = _current_incoming(state)
    bundle = freeze_current_execution_authority(selection_snapshot=snapshot, switch_incoming=[incoming])
    candidates = discover_candidates(snapshot=snapshot)["candidates"]
    first = enrich_discovered_candidates(selection_snapshot=snapshot, execution_bundle=bundle, candidates=candidates)
    second = enrich_discovered_candidates(selection_snapshot=snapshot, execution_bundle=bundle, candidates=list(reversed(candidates)))

    assert {row["candidate_id"]: row["execution_readiness"] for row in first["candidates"]} == {row["candidate_id"]: row["execution_readiness"] for row in second["candidates"]}
    assert next(row for row in first["candidates"] if row["candidate_id"] == "manual_switch:bench-b")["execution_reason"] == "incoming_state_unavailable"
    bad_bundle = {**bundle, "decision_branch_fingerprint": "stale"}
    assert enrich_discovered_candidates(selection_snapshot=snapshot, execution_bundle=bad_bundle, candidates=candidates)["reason"] == "selection_execution_d0_mismatch"
    foreign = _current_incoming(state)
    foreign["owner"] = {**foreign["owner"], "side": "opponent"}
    assert freeze_current_execution_authority(selection_snapshot=snapshot, switch_incoming=[foreign])["status"] == "rejected"


def test_mixed_discovery_enrichment_materialization_and_ranking_preserve_uncertainty():
    state, _ = _state()
    owner = _owner(state, "self")
    snapshot = _selection(state)
    bundle = freeze_current_execution_authority(selection_snapshot=snapshot, switch_incoming=[_current_incoming(state)])
    discovered = discover_candidates(snapshot=snapshot)["candidates"]
    enriched = enrich_discovered_candidates(selection_snapshot=snapshot, execution_bundle=bundle, candidates=discovered)
    materialized = materialize_candidates(decision_state=state, decision_owner=owner, candidates=enriched["candidates"])

    statuses = {result.get("candidate_id", result.get("outcome", {}).get("candidate_id")): result["status"] for result in materialized["outcomes"]}
    assert statuses == {"attack:water-gun": "incomplete", "manual_switch:incoming": "complete"}
    assert state["active"]["self"]["pokemon_id"] != "incoming"
    complete = next(result["outcome"] for result in materialized["outcomes"] if result["status"] == "complete")
    incomplete = next(result for result in materialized["outcomes"] if result["status"] == "incomplete")
    assert rank_candidates(decision_owner=owner, candidates=[complete, incomplete])["status"] == "incomplete_comparison_set"


def test_stale_source_or_selection_owner_mismatch_is_rejected():
    state, _ = _state()
    snapshot = _selection(state)
    stale = _current_incoming(state)
    stale["source_branch_fingerprint"] = "stale"
    assert freeze_current_execution_authority(selection_snapshot=snapshot, switch_incoming=[stale])["status"] == "rejected"
    bundle = freeze_current_execution_authority(selection_snapshot=snapshot, switch_incoming=[_current_incoming(state)])
    wrong_owner = deepcopy(snapshot)
    wrong_owner["decision_owner"]["pokemon_id"] = "foreign"
    assert enrich_discovered_candidates(selection_snapshot=wrong_owner, execution_bundle=bundle, candidates=[])["status"] == "rejected"
