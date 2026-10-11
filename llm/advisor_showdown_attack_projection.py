"""Strict HP-only compatibility for proven native fixed-damage move attempts."""
from copy import deepcopy
from llm.advisor_showdown_outcome_evidence import validate_native_selected_action_outcome
from llm.advisor_reducer_state_model import is_unknown_battle_fact, state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


def project_native_fixed_damage_attempt(*, evidence, base, runtime_snapshot):
    checked = validate_native_selected_action_outcome(evidence=evidence, base=base, runtime_snapshot=runtime_snapshot)
    if checked["status"] != "resolved":
        return checked
    if evidence["evidence_class"] != "native_conditional_exact":
        return _error("rejected", "native_attack_requires_conditional_exact")
    if base["move_id"] not in {"seismic-toss", "night-shade"}:
        return _error("unsupported", "native_attack_compatible_family_unsupported")
    try:
        row = evidence["native_outcome"]
        if any(line.startswith("|cant|") for line in row["events"]):
            return _error("rejected", "native_attack_action_was_cancelled")
        before, after = deepcopy(row["before"]), deepcopy(row["after"])
        state = deepcopy(runtime_snapshot["state"])
        hp_changes = {}
        for owner in (base["actor"], base["target"]):
            side, slot = owner["side"], owner["slot_index"]
            source = state[f"{side}_side"]["pokemon"]
            source = source.get(slot, source.get(str(slot)))
            pre = next(p for p in before["sides"][side]["pokemon"] if p["slot_index"] == slot)
            post = next(p for p in after["sides"][side]["pokemon"] if p["slot_index"] == slot)
            if (type(source["current_hp"]) is not int or type(source["max_hp"]) is not int or
                (source["current_hp"], source["max_hp"], source["fainted"]) != (pre["hp"], pre["max_hp"], pre["fainted"])):
                return _error("rejected", "native_attack_observed_hp_required")
            if source.get("current_opponent_response_set", {}).get("move_pp_slots") is not None:
                return _error("unsupported", "native_attack_known_pp_projection_unsupported")
            for key, participant in (("root_checkpoint", pre), ("checkpoint", post)):
                saved = next(p for p in row[key]["native_state"]["sides"][0 if side == "self" else 1]["pokemon"] if p["set"]["name"] == f"slot-{slot}")
                if (saved["hp"], saved["maxhp"], saved["fainted"]) != (participant["hp"], participant["max_hp"], participant["fainted"]):
                    return _error("rejected", "native_attack_summary_checkpoint_contradiction")
            if pre["received_hit_count"] != post["received_hit_count"]:
                counter = source.get("rage_fist_hit_count")
                if counter is not None and not is_unknown_battle_fact(counter):
                    return _error("unsupported", "native_attack_known_hit_count_projection_unsupported")
                pre["received_hit_count"] = post["received_hit_count"]
            hp_changes[side] = {"pre_hp": pre["hp"], "post_hp": post["hp"], "fainted": post["fainted"]}
            pre["hp"], pre["fainted"] = post["hp"], post["fainted"]
            if post["fainted"] and pre["active"] and not post["active"]:
                # The legacy view retains the fainted slot until a replacement;
                # native inactive/request/queue identity stays in the evidence.
                pre["active"] = post["active"]
            source["current_hp"], source["fainted"] = post["hp"], post["fainted"]
            if owner == base["actor"]:
                for first, last in zip(pre["moves"], post["moves"], strict=True):
                    if first["id"] == base["move_id"].replace("-", ""):
                        if not 0 < first["pp"] - last["pp"] <= first["pp"]:
                            return _error("rejected", "native_attack_selected_pp_contradiction")
                        first["pp"] = last["pp"]
        for view in (before, after):
            view.pop("request_state")
            view.pop("decision_phase")
            for side in view["sides"].values():
                side.pop("request")
        if before != after:
            return _error("unsupported", "native_attack_additional_effect_projection_unsupported")
        snapshot = {"status": "runtime_snapshot_ready", "session_id": base["session_id"], "state": state, "state_fingerprint": state_fingerprint(state)}
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=base["actor"])
        if d0.get("status") != "resolved":
            return _error("unsupported", "native_attack_post_state_projection_unsupported")
        return {"status": "resolved", "post_action_runtime_snapshot": snapshot, "post_action_strategy_d0": d0,
            "action_consequence": {"schema_version": "showdown-compatible-fixed-damage-attempt-v1", "hp_changes": hp_changes,
                "evidence_class": evidence["evidence_class"], "probability_scope": deepcopy(evidence["probability_scope"]),
                "native_outcome_evidence": deepcopy(evidence)}, "probability": deepcopy(evidence["branches"][0]["probability"])}
    except (KeyError, TypeError, AttributeError, StopIteration, ValueError):
        return _error("rejected", "native_attack_projection_shape_invalid")


def _error(status, reason):
    return {"status": status, "reason": reason}
