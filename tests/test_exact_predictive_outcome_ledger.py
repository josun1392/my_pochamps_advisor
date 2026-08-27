from copy import deepcopy

from llm.advisor_exact_predictive_outcome_ledger import normalize_exact_predictive_outcome_ledger


OWNER = {"side": "self", "session_id": "ledger-session", "slot_index": 0, "pokemon_id": "p1"}
TARGET = {"side": "opponent", "session_id": "ledger-session", "slot_index": 0, "pokemon_id": "p2"}


def _candidate(move="shadow-ball"):
    return {"candidate_id": f"attack:{move}", "action_type": "attack", "session_id": "ledger-session", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER)}


def _bindings(move="shadow-ball"):
    return {"session_id": "ledger-session", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "decision_owner": deepcopy(OWNER), "attacker": deepcopy(OWNER), "target": deepcopy(TARGET), "move_id": move}


def _manifest(*, critical="not_applicable", secondary="not_applicable"):
    return {"accuracy": {"status": "resolved"}, "critical": {"status": critical}, "damage_roll": {"status": "resolved"}, "secondary": {"status": secondary}}


def _rolls(move="shadow-ball", *, critical=None):
    # Roll ledgers inherit runtime/identity from their bound hit/crit parent.
    bound = _bindings(move)
    return {"status": "resolved", "schema_version": "deterministic-predictive-damage-roll-uncertainty-v1", "session_id": bound["session_id"], "source_branch_fingerprint": bound["source_branch_fingerprint"], "decision_owner": bound["decision_owner"], "move_id": move, "critical_scope": critical, "outcomes": tuple({"roll_index": i, "random_factor_percent": 85 + i, "damage": 9 if i < 2 else 10, "probability": {"numerator": 1, "denominator": 16}, "post_hit_consequence": {"attacker_post_hit_hp": 90 - i} } for i in range(16))}


def _consequences(move="shadow-ball", *, critical=None, secondary=None):
    result = {"interval": {"target_hp_before": 20}, "damage_roll_uncertainty": _rolls(move, critical=critical)}
    if secondary is not None:
        result[secondary[0]] = secondary[1]
    return result


def _hit(move="shadow-ball", *, critical="not_applicable", secondary=None, probability=80):
    base = _consequences(move, secondary=secondary)
    if critical == "resolved":
        non = _consequences(move, critical="non_critical", secondary=secondary)
        crit = _consequences(move, critical="critical", secondary=secondary)
        base = {"critical_hit_uncertainty": {"status": "resolved", "schema_version": "deterministic-predictive-critical-hit-uncertainty-v1", **_bindings(move), "critical_probability": {"numerator": 1, "denominator": 4}, "branches": ({"branch": "non_critical", "conditional_critical_probability": {"numerator": 3, "denominator": 4}, "consequences": non}, {"branch": "critical", "conditional_critical_probability": {"numerator": 1, "denominator": 4}, "consequences": crit})}}
    hit = {"branch": "hit", "probability_percent": probability, "consequences": base}
    miss = {"branch": "miss", "probability_percent": 100 - probability, "consequences": {"target_damage": 0, "attacker_hp_after": 100}}
    branches = (miss,) if probability == 0 else (hit,) if probability == 100 else (hit, miss)
    return {"status": "resolved", "schema_version": "deterministic-predictive-hit-miss-uncertainty-v1", **_bindings(move), "probability_percent": probability, "branches": branches}


def _secondary(schema, *, move="shadow-ball", per_roll=False):
    result = {"status": "resolved", "schema_version": schema, **_bindings(move)}
    if not per_roll:
        result["branches"] = ({"branch": "no_effect", "conditional_secondary_probability": {"numerator": 90, "denominator": 100}}, {"branch": "effect", "conditional_secondary_probability": {"numerator": 10, "denominator": 100}, "hypothetical_stage_effect": {"owner": "self", "stat": "attack", "delta": 1}})
    else:
        leaves = []
        for i in range(16):
            row = {"roll_index": i, "damage": 9 if i < 2 else 10, "secondary_eligibility": "eligible", "secondary_branches": ({"branch": "no_effect", "conditional_secondary_probability": {"numerator": 80, "denominator": 100}}, {"branch": "effect", "conditional_secondary_probability": {"numerator": 20, "denominator": 100}, "hypothetical_stage_effect": {"owner": "target", "stat": "special-defense", "delta": -1}})}
            leaves.append(row)
        result["damage_roll_leaves"] = tuple(leaves)
    return result


def test_hit_crit_and_all_sixteen_roll_identities_normalize_exactly():
    result = normalize_exact_predictive_outcome_ledger(candidate=_candidate(), predictive_consequence=_hit(critical="resolved"), component_manifest=_manifest(critical="resolved"), bindings=_bindings())
    assert result["status"] == "evaluable"
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert len(result["terminal_leaves"]) == 33  # miss + 16 non-crit + 16 crit
    rolls = [leaf for leaf in result["terminal_leaves"] if leaf["damage_roll"]]
    assert [leaf["damage_roll"]["roll_index"] for leaf in rolls[:16]] == list(range(16))
    assert rolls[0]["consequences"]["damage"] == rolls[1]["consequences"]["damage"] == 9
    assert rolls[0]["leaf_id"] != rolls[1]["leaf_id"]
    assert rolls[0]["consequences"]["own_final_hp"] == 90
    assert next(leaf for leaf in result["terminal_leaves"] if leaf["hit_state"] == "miss")["probability"] == {"numerator": 1, "denominator": 5}


def test_self_secondary_composes_exactly_on_each_successful_roll():
    secondary = ("probabilistic_self_stage_effect_uncertainty", _secondary("deterministic-predictive-probabilistic-self-stage-effect-uncertainty-v1", move="metal-claw"))
    result = normalize_exact_predictive_outcome_ledger(candidate=_candidate("metal-claw"), predictive_consequence=_hit("metal-claw", secondary=secondary, probability=100), component_manifest=_manifest(secondary="resolved"), bindings=_bindings("metal-claw"))
    assert result["status"] == "evaluable"
    effects = [leaf for leaf in result["terminal_leaves"] if leaf["consequences"]["secondary"] and leaf["consequences"]["secondary"]["branch"] == "effect"]
    assert len(effects) == 16
    assert effects[0]["probability"] == {"numerator": 1, "denominator": 160}


def test_target_secondary_uses_matching_surviving_roll_identity_and_preserves_probability():
    secondary = ("probabilistic_target_stage_effect_uncertainty", _secondary("deterministic-predictive-probabilistic-target-stage-effect-uncertainty-v1", per_roll=True))
    result = normalize_exact_predictive_outcome_ledger(candidate=_candidate(), predictive_consequence=_hit(secondary=secondary, probability=100), component_manifest=_manifest(secondary="resolved"), bindings=_bindings())
    assert result["status"] == "evaluable"
    effects = [leaf for leaf in result["terminal_leaves"] if leaf["consequences"]["secondary"] and leaf["consequences"]["secondary"]["branch"] == "effect"]
    assert len(effects) == 16
    assert effects[0]["probability"] == {"numerator": 1, "denominator": 80}


def test_survival_required_thunderbolt_secondary_has_no_descendant_for_ko_roll():
    status = _secondary("deterministic-predictive-thunderbolt-paralysis-uncertainty-v1", move="thunderbolt", per_roll=True)
    status["damage_roll_leaves"] = tuple({**row, "secondary_branches": ()} if row["roll_index"] == 0 else row for row in status["damage_roll_leaves"])
    status["damage_roll_leaves"][0]["secondary_eligibility"] = "target_fainted"
    secondary = ("thunderbolt_paralysis_uncertainty", status)
    result = normalize_exact_predictive_outcome_ledger(candidate=_candidate("thunderbolt"), predictive_consequence=_hit("thunderbolt", secondary=secondary, probability=100), component_manifest=_manifest(secondary="resolved"), bindings=_bindings("thunderbolt"))
    assert result["status"] == "evaluable"
    ko_roll = [leaf for leaf in result["terminal_leaves"] if leaf["damage_roll"] and leaf["damage_roll"]["roll_index"] == 0]
    assert len(ko_roll) == 1 and ko_roll[0]["consequences"]["secondary"]["branch"] == "not_applicable"


def test_iron_head_flinch_secondary_normalizes_exactly_without_erasing_roll_identity():
    flinch = _secondary("deterministic-predictive-iron-head-flinch-uncertainty-v1", move="iron-head", per_roll=True)
    flinch["damage_roll_leaves"] = tuple(
        {
            **row,
            "secondary_branches": (
                {"branch": "no_effect", "conditional_secondary_probability": {"numerator": 70, "denominator": 100}},
                {"branch": "effect", "conditional_secondary_probability": {"numerator": 30, "denominator": 100}, "hypothetical_target_flinch": {"schema_version": "detached-hypothetical-immediate-flinch-v1", "state": "flinched"}},
            ),
        }
        for row in flinch["damage_roll_leaves"]
    )
    result = normalize_exact_predictive_outcome_ledger(candidate=_candidate("iron-head"), predictive_consequence=_hit("iron-head", secondary=("iron_head_flinch_uncertainty", flinch), probability=100), component_manifest=_manifest(secondary="resolved"), bindings=_bindings("iron-head"))
    assert result["status"] == "evaluable"
    assert result["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    effects = [leaf for leaf in result["terminal_leaves"] if leaf["consequences"]["secondary"] and leaf["consequences"]["secondary"]["branch"] == "effect"]
    assert len(effects) == 16
    assert effects[0]["consequences"]["secondary"]["hypothetical_target_flinch"]["state"] == "flinched"


def test_missing_manifest_and_partial_or_stale_tree_fail_closed_without_renormalization():
    assert normalize_exact_predictive_outcome_ledger(candidate=_candidate(), predictive_consequence=_hit(), component_manifest={"accuracy": {"status": "resolved"}}, bindings=_bindings())["status"] == "incomplete"
    partial = _hit(); partial["branches"] = (partial["branches"][0],)
    rejected = normalize_exact_predictive_outcome_ledger(candidate=_candidate(), predictive_consequence=partial, component_manifest=_manifest(), bindings=_bindings())
    assert rejected["status"] == "rejected" and rejected["reason"] == "hit_miss_probability_mass_invalid"
    stale = _bindings(); stale["source_runtime_fingerprint"] = "other"
    assert normalize_exact_predictive_outcome_ledger(candidate=_candidate(), predictive_consequence=_hit(), component_manifest=_manifest(), bindings=stale)["status"] == "rejected"


def test_explicit_zero_probability_secondary_creates_only_no_effect_leaf_and_manual_switch_is_one_over_one():
    secondary = _secondary("deterministic-predictive-probabilistic-self-stage-effect-uncertainty-v1", move="metal-claw")
    secondary["branches"] = ({"branch": "no_effect", "conditional_secondary_probability": {"numerator": 100, "denominator": 100}},)
    attack = normalize_exact_predictive_outcome_ledger(candidate=_candidate("metal-claw"), predictive_consequence=_hit("metal-claw", secondary=("probabilistic_self_stage_effect_uncertainty", secondary), probability=100), component_manifest=_manifest(secondary="resolved"), bindings=_bindings("metal-claw"))
    assert attack["status"] == "evaluable" and len(attack["terminal_leaves"]) == 16
    switch_owner = deepcopy(OWNER)
    candidate = {"candidate_id": "switch:p3", "action_type": "manual_switch", "session_id": "ledger-session", "source_branch_fingerprint": "preview", "decision_owner": switch_owner}
    outcome = {"status": "complete", "outcome": {"schema_version": "deterministic-candidate-outcome-v1", "candidate_id": "switch:p3", "action_type": "manual_switch", "source_branch_fingerprint": "preview", "completeness": "complete"}}
    bindings = {"session_id": "ledger-session", "source_runtime_fingerprint": "runtime", "source_branch_fingerprint": "preview", "decision_owner": switch_owner}
    switch = normalize_exact_predictive_outcome_ledger(candidate=candidate, predictive_consequence=outcome, component_manifest={name: {"status": "not_applicable"} for name in ("accuracy", "critical", "damage_roll", "secondary")}, bindings=bindings)
    assert switch["status"] == "evaluable" and switch["terminal_leaves"][0]["probability"] == {"numerator": 1, "denominator": 1}
