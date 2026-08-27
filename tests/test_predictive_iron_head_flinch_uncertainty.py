from copy import deepcopy

from advisor.probabilistic_target_flinch_effect_capabilities import resolve_probabilistic_target_flinch_effect_capability
from llm.advisor_predictive_iron_head_flinch_uncertainty import compose_predictive_iron_head_flinch_uncertainty


OWNER = {"session_id": "flinch", "side": "self", "slot_index": 0, "pokemon_id": "attacker"}
TARGET = {"session_id": "flinch", "side": "opponent", "slot_index": 0, "pokemon_id": "target"}
MOVE = {"move_id": "iron-head", "category": "physical", "power": 80, "target": "selected-pokemon", "effect_chance": 30, "ailment": "flinch"}


def _authority():
    capability = resolve_probabilistic_target_flinch_effect_capability(move=MOVE, source_authority={"attacker_ability": {"status": "known", "value": "pressure"}, "target_ability": {"status": "known", "value": "pressure"}, "target_item": {"status": "known_absent"}})
    return {"status": "resolved", "schema_version": "runtime-d0-iron-head-flinch-authority-v1", "session_id": "flinch", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "branch", "decision_owner": OWNER, "attacker": OWNER, "target": TARGET, "move": MOVE, "capability_resolution": capability, "target_substitute_authority": {"status": "known", "state": "known_inactive"}}


def _interval(hp=100):
    return {"completeness": "exact_complete", "move_id": "iron-head", "session_id": "flinch", "source_branch_fingerprint": "branch", "decision_owner": OWNER, "target_routing": "target", "target_hp_before": hp, "exact_damage_rolls": tuple(10 for _ in range(16))}


def test_iron_head_canonical_flinch_branches_exactly_after_surviving_hits():
    candidate = {"candidate_id": "attack:iron-head", "action_type": "attack", "session_id": "flinch", "source_branch_fingerprint": "branch", "decision_owner": OWNER}
    result = compose_predictive_iron_head_flinch_uncertainty(candidate=candidate, interval=_interval(), runtime_authority=_authority())
    assert result["status"] == "resolved"
    assert all(tuple(branch["branch"] for branch in row["secondary_branches"]) == ("no_effect", "effect") for row in result["damage_roll_leaves"])
    assert result["damage_roll_leaves"][0]["secondary_branches"][1]["conditional_secondary_probability"] == {"numerator": 30, "denominator": 100}


def test_flinch_is_absent_on_ko_and_metadata_or_modifier_mismatch_fails_closed():
    candidate = {"candidate_id": "attack:iron-head", "action_type": "attack", "session_id": "flinch", "source_branch_fingerprint": "branch", "decision_owner": OWNER}
    ko = compose_predictive_iron_head_flinch_uncertainty(candidate=candidate, interval=_interval(5), runtime_authority=_authority())
    assert all(row["secondary_branches"] == () for row in ko["damage_roll_leaves"])
    bad = deepcopy(MOVE); bad["effect_chance"] = 20
    assert resolve_probabilistic_target_flinch_effect_capability(move=bad, source_authority={"attacker_ability": {"status": "known", "value": "pressure"}, "target_ability": {"status": "known", "value": "pressure"}, "target_item": {"status": "known_absent"}})["status"] == "unsupported"
