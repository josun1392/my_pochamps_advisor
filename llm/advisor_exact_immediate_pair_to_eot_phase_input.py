"""Strict bridge from one exact immediate-pair leaf to the exact EOT input."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_end_of_turn_residual_phase import freeze_end_of_turn_phase_input


SCHEMA_VERSION = "detached-immediate-pair-terminal-eot-active-authority-v1"
_SIDES = ("self", "opponent")
_BASE = ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def materialize_exact_immediate_pair_to_eot_phase_input(
    *, terminal_ledger: Mapping[str, Any], terminal_leaf_id: str,
    terminal_active_authorities: Mapping[str, Any],
    weather_authority: Mapping[str, Any] | None = None,
    leech_seed_transfers: tuple[Mapping[str, Any], ...] = (),
) -> dict[str, Any]:
    """Bind one evaluated pair leaf to the existing exact EOT input contract.

    ``terminal_active_authorities`` is the narrow handoff from existing D0
    and path-local owners.  It deliberately carries no HP: final HP/faint is
    derived only from the selected pair leaf, so a root-state value cannot
    overwrite an action consequence.
    """
    base, leaf = _source(terminal_ledger, terminal_leaf_id)
    if base is None:
        return _result("rejected", "exact_immediate_pair_terminal_source_invalid")
    if not isinstance(terminal_active_authorities, Mapping) or set(terminal_active_authorities) != set(_SIDES):
        return _result("rejected", "exact_eot_terminal_active_authorities_invalid", base)
    rows: dict[str, dict[str, Any]] = {}
    for side, hp_key, owner_key in (("self", "own_final_hp", "own_actor"), ("opponent", "opponent_final_hp", "opponent_actor")):
        row = _active_row(terminal_active_authorities[side], base, leaf, side, hp_key, owner_key)
        if isinstance(row, str):
            return _result("incomplete" if row.endswith("_unknown") else "rejected", row, base)
        item = _path_local_item(leaf, row["owner"], base)
        if isinstance(item, str):
            return _result("incomplete", item, base)
        condition = _path_local_condition(leaf, row["owner"], base)
        if isinstance(condition, str):
            return _result("incomplete", condition, base)
        rows[side] = {**row, "item": item if item is not None else row["item"], "condition": condition if condition is not None else row["condition"]}
    frozen = freeze_end_of_turn_phase_input(
        terminal_ledger=terminal_ledger, terminal_leaf_id=terminal_leaf_id,
        active_states=rows, weather_authority=weather_authority,
        leech_seed_transfers=leech_seed_transfers,
    )
    if frozen.get("status") != "resolved":
        return deepcopy(dict(frozen))
    return {**deepcopy(dict(frozen)), "provenance": "strict_exact_immediate_pair_terminal_to_eot_phase_input_adapter_v1"}


def _source(ledger: Any, leaf_id: Any) -> tuple[dict[str, Any] | None, Mapping[str, Any] | None]:
    if not isinstance(ledger, Mapping) or ledger.get("status") != "evaluable" or ledger.get("schema_version") != "exact-immediate-action-pair-outcome-ledger-v1" or ledger.get("terminal_probability_mass") != {"numerator": 1, "denominator": 1} or not isinstance(leaf_id, str) or not leaf_id:
        return None, None
    if any(not isinstance(ledger.get(key), str) or not ledger[key] for key in ("pair_id", "session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) or not isinstance(ledger.get("decision_owner"), Mapping):
        return None, None
    leaves = ledger.get("terminal_leaves")
    matches = [leaf for leaf in leaves if isinstance(leaf, Mapping) and leaf.get("pair_leaf_id") == leaf_id] if isinstance(leaves, (tuple, list)) else []
    if len(matches) != 1:
        return None, None
    leaf = matches[0]
    final = leaf.get("final_consequences")
    if not isinstance(final, Mapping) or any(not _hp(final.get(key)) for key in ("own_final_hp", "opponent_final_hp")):
        return None, None
    base = {key: deepcopy(ledger[key]) for key in _BASE}
    if not _owner(ledger.get("own_actor"), ledger["session_id"]) or not _owner(ledger.get("opponent_actor"), ledger["session_id"]):
        return None, None
    base["own_actor"] = deepcopy(dict(ledger["own_actor"]))
    base["opponent_actor"] = deepcopy(dict(ledger["opponent_actor"]))
    return base, leaf


def _active_row(value: Any, base: Mapping[str, Any], leaf: Mapping[str, Any], side: str, hp_key: str, owner_key: str) -> dict[str, Any] | str:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != SCHEMA_VERSION or value.get("terminal_leaf_id") != leaf.get("pair_leaf_id"):
        return "exact_eot_terminal_active_authority_invalid"
    if any(value.get(key) != base[key] for key in _BASE):
        return "exact_eot_terminal_active_authority_binding_mismatch"
    owner = value.get("owner")
    if not _owner(owner, base["session_id"]) or owner != base[owner_key]:
        return "exact_eot_terminal_active_owner_mismatch"
    maximum = value.get("maximum_hp")
    final = leaf["final_consequences"][hp_key]
    if not _positive(maximum) or final > maximum:
        return "exact_eot_terminal_max_hp_unknown"
    source_binding = {"session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "owner": deepcopy(dict(owner))}
    fields = ("condition", "item", "toxic_progression", "speed", "ability", "persistent_effects")
    if any(not isinstance(value.get(key), Mapping) for key in fields):
        return "exact_eot_terminal_state_authority_unknown"
    types = value.get("types")
    if types is not None and not isinstance(types, Mapping):
        return "exact_eot_terminal_type_authority_invalid"
    # Every source must carry the exact D0 binding.  Leaf-local condition and
    # item effects additionally retain their source leaf in their own schema.
    for key in ("condition", "item", "toxic_progression", "speed", "ability") + (("types",) if types is not None else ()):
        authority = value[key]
        if authority.get("source_binding") != source_binding:
            return "exact_eot_terminal_state_authority_binding_mismatch"
    persistent = value["persistent_effects"]
    if set(persistent) != {"aqua_ring", "ingrain"} or any(not isinstance(authority, Mapping) or authority.get("source_binding") != source_binding for authority in persistent.values()):
        return "exact_eot_terminal_state_authority_binding_mismatch"
    if value["condition"].get("status") == "unknown" or value["item"].get("status") == "unknown" or value["ability"].get("status") == "unknown" or any(authority.get("status") == "unknown" for authority in persistent.values()):
        return "exact_eot_terminal_state_authority_unknown"
    if value["condition"].get("condition") == "toxic" and value["toxic_progression"].get("status") != "known":
        return "exact_eot_terminal_toxic_authority_unknown"
    return {
        "owner": deepcopy(dict(owner)),
        "hp": {"status": "known", "current_hp": final, "maximum_hp": maximum, "source_terminal_leaf_id": leaf["pair_leaf_id"]},
        "fainted": {"status": "known", "value": final == 0, "source_terminal_leaf_id": leaf["pair_leaf_id"]},
        **{key: deepcopy(dict(value[key])) for key in fields},
        **({"types": deepcopy(dict(types))} if types is not None else {}),
    }


def _path_local_item(leaf: Mapping[str, Any], owner: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any] | str | None:
    actions = [leaf.get("first_action")]
    second = leaf.get("second_action")
    if isinstance(second, Mapping): actions.append(second.get("leaf"))
    result = None
    for action in actions:
        consequences = action.get("consequences") if isinstance(action, Mapping) else None
        if not isinstance(consequences, Mapping):
            continue
        sitrus = consequences.get("sitrus_berry_immediate_consumption")
        if isinstance(sitrus, Mapping) and sitrus.get("status") == "resolved" and sitrus.get("outcome") == "activated":
            if sitrus.get("holder") != dict(owner):
                continue
            if sitrus.get("item_after") != {"status": "known_absent", "value": None, "consumption_cause": "sitrus_berry"}:
                return "exact_eot_terminal_sitrus_item_consequence_invalid"
            if not _bound_action(action, base) or sitrus.get("source_leaf_id") != action.get("leaf_id") or any(sitrus.get(key) != base[key] for key in _BASE):
                return "exact_eot_terminal_sitrus_item_binding_invalid"
            result = {"status": "known_absent", "source_binding": {"session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "owner": deepcopy(dict(owner))}, "source_terminal_leaf_id": leaf["pair_leaf_id"], "provenance": "exact_terminal_sitrus_consumption"}
        elif any(key in consequences for key in ("knock_off_item_removal", "item_transfer_after_hit", "atomic_item_swap")):
            return "exact_eot_terminal_item_mutation_unrepresented"
    return result


def _path_local_condition(leaf: Mapping[str, Any], owner: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any] | str | None:
    result = None
    actions = [leaf.get("first_action")]
    second = leaf.get("second_action")
    if isinstance(second, Mapping): actions.append(second.get("leaf"))
    binding = {"session_id": base["session_id"], "source_runtime_fingerprint": base["source_runtime_fingerprint"], "source_branch_fingerprint": base["source_branch_fingerprint"], "owner": deepcopy(dict(owner))}
    for action in actions:
        if not isinstance(action, Mapping): continue
        provenance, consequences = action.get("provenance"), action.get("consequences")
        secondary = consequences.get("secondary") if isinstance(consequences, Mapping) else None
        if not isinstance(provenance, Mapping) or not isinstance(secondary, Mapping): continue
        if not _bound_action(action, base): return "exact_eot_terminal_condition_binding_invalid"
        if provenance.get("target") != dict(owner): continue
        applied = secondary.get("hypothetical_target_condition")
        removed = secondary.get("hypothetical_target_condition_removal")
        if isinstance(applied, Mapping):
            condition = applied.get("resulting_condition")
            if condition not in {"burn", "poison", "toxic", "paralysis", "sleep", "freeze"}:
                return "exact_eot_terminal_condition_consequence_invalid"
            result = {"status": "known_present", "condition": condition, "source_binding": binding, "source_terminal_leaf_id": leaf["pair_leaf_id"], "hypothetical_condition_authority": {"status": "known_present", "condition": condition}, "provenance": "exact_terminal_condition_application"}
        elif isinstance(removed, Mapping):
            if removed.get("condition_after") != "none":
                return "exact_eot_terminal_condition_consequence_invalid"
            result = {"status": "known_none", "source_binding": binding, "source_terminal_leaf_id": leaf["pair_leaf_id"], "provenance": "exact_terminal_condition_removal"}
    return result


def _owner(value: Any, session: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and value.get("session_id") == session and value.get("side") in _SIDES and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _hp(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and value >= 0
def _positive(value: Any) -> bool: return _hp(value) and value > 0
def _bound_action(action: Any, base: Mapping[str, Any]) -> bool:
    return isinstance(action, Mapping) and isinstance(action.get("leaf_id"), str) and bool(action["leaf_id"]) and isinstance(action.get("provenance"), Mapping) and all(action["provenance"].get(key) == base[key] for key in _BASE)
def _result(status: str, reason: str, base: Mapping[str, Any] | None = None) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, **(deepcopy(dict(base)) if base else {}), "reason": reason}
