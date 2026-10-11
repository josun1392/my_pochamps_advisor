"""Opt-in native HP consequence for the existing plain-heal selected consumer."""
from copy import deepcopy
from collections.abc import Mapping

from llm.advisor_showdown_outcome_evidence import validate_native_selected_action_outcome

SCHEMA_VERSION = "showdown-compatible-direct-heal-v1"


def materialize_native_direct_heal(*, evidence, base, runtime_snapshot, execution_authority):
    try:
        return _materialize(evidence=evidence, base=base, runtime_snapshot=runtime_snapshot, execution_authority=execution_authority)
    except (KeyError, TypeError, AttributeError, StopIteration, ValueError):
        return _error("rejected", "native_direct_heal_shape_invalid", base)


def _materialize(*, evidence, base, runtime_snapshot, execution_authority):
    checked = validate_native_selected_action_outcome(evidence=evidence, base=base, runtime_snapshot=runtime_snapshot)
    if checked["status"] != "resolved":
        return checked
    if evidence["evidence_class"] != "native_conditional_exact":
        return _error("rejected", "native_direct_heal_requires_conditional_exact", base)
    if (not isinstance(execution_authority, Mapping) or execution_authority.get("status") != "resolved" or
        any(execution_authority.get(k) != base[k] for k in base if k != "target") or
        execution_authority.get("canonical_effect", {}).get("effect", {}).get("consequence_family") != "plain_half_max_hp_self_heal"):
        return _error("rejected", "native_direct_heal_catalog_binding_invalid", base)
    row, actor = evidence["native_outcome"], base["actor"]
    source = runtime_snapshot["state"][f"{actor['side']}_side"]["pokemon"]
    source = source.get(actor["slot_index"], source.get(str(actor["slot_index"])))
    if source.get("current_opponent_response_set", {}).get("move_pp_slots") is not None:
        return _error("unsupported", "native_direct_heal_known_pp_projection_unsupported", base)
    if any(line.startswith("|cant|") for line in row["events"]):
        return _error("rejected", "native_direct_heal_action_was_cancelled", base)
    before, after = deepcopy(row["before"]), deepcopy(row["after"])
    if before["turn"] != after["turn"] or before["ended"] != after["ended"]:
        return _error("unsupported", "native_direct_heal_extended_phase_projection_unsupported", base)
    pre = _participant(before, actor)
    post = _participant(after, actor)
    # Read HP from native serialization as well as its structured summary.
    for key, view in (("root_checkpoint", pre), ("checkpoint", post)):
        participants = row[key]["native_state"]["sides"][0 if actor["side"] == "self" else 1]["pokemon"]
        saved = next(p for p in participants if p["set"]["name"] == f"slot-{actor['slot_index']}")
        if (saved["hp"], saved["maxhp"], saved["fainted"]) != (view["hp"], view["max_hp"], view["fainted"]):
            return _error("rejected", "native_direct_heal_summary_checkpoint_contradiction", base)
    if (pre["hp"] != source["current_hp"] or pre["max_hp"] != source["max_hp"] or
        pre["fainted"] is not False or post["max_hp"] != pre["max_hp"] or
        not pre["hp"] <= post["hp"] <= pre["max_hp"]):
        return _error("rejected", "native_direct_heal_observed_hp_contradiction", base)
    pre_hp, maximum, post_hp = pre["hp"], pre["max_hp"], post["hp"]
    if post_hp == pre_hp and pre_hp < maximum:
        return _error("rejected", "native_direct_heal_no_effect_contradicts_plain_heal", base)
    pre["hp"] = post["hp"]
    # Preserve native PP in the attached checkpoint; the legacy HP-only view
    # cannot update an observed PP record. Reject any other participant change.
    for first, last in zip(pre["moves"], post["moves"], strict=True):
        if first["id"] == "".join(c for c in base["move_id"] if c.isalnum()):
            if not 0 < first["pp"] - last["pp"] <= first["pp"]:
                return _error("rejected", "native_direct_heal_selected_pp_contradiction", base)
            first["pp"] = last["pp"]
    for view in (before, after):
        for key in ("request_state", "decision_phase"):
            view.pop(key)
        for side in view["sides"].values():
            side.pop("request")
    if before != after:
        return _error("unsupported", "native_direct_heal_additional_effect_projection_unsupported", base)
    return {"status": "resolved", "schema_version": SCHEMA_VERSION, **deepcopy(base),
        "outcome": "healed" if post_hp > pre_hp else "no_effect_full_hp",
        "probability": deepcopy(evidence["branches"][0]["probability"]),
        "heal": {"pre_hp": pre_hp, "max_hp": maximum, "actual_heal": post_hp - pre_hp, "post_hp": post_hp},
        "evidence_class": evidence["evidence_class"], "probability_scope": deepcopy(evidence["probability_scope"]),
        "native_outcome_evidence": deepcopy(evidence),
        "provenance": "native_constant_rng_attempt_to_compatible_detached_hp_v1"}


def _participant(view, owner):
    return next(p for p in view["sides"][owner["side"]]["pokemon"] if p["slot_index"] == owner["slot_index"])


def _error(status, reason, base):
    return {"status": status, "schema_version": SCHEMA_VERSION, **deepcopy(base), "reason": reason}
