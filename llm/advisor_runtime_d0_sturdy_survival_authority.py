"""Frozen, identity-bound current Sturdy survival authority for one attack."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_ability_interaction_authority import normalize_ability_applicability_context
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_strategy_d0 import runtime_strategy_d0_freshness


SCHEMA_VERSION = "runtime-d0-sturdy-survival-authority-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def bind_sturdy_survival_authority_through_actor_neutral_root(
    *, strategy_d0: Mapping[str, Any], root_predictive_authority: Mapping[str, Any],
    sturdy_survival_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one D0-bound Sturdy fact into the opponent-first root.

    The root owns its synthetic predictive D0.  This narrow adapter changes
    only the branch binding after proving that the original action, attacker,
    and defender are identical.  It never derives Sturdy from an actor side.
    """
    base = _root_binding(strategy_d0, root_predictive_authority)
    if isinstance(base, str):
        return {"status": "rejected", "reason": base}
    source = _source_binding(sturdy_survival_authority, base)
    if isinstance(source, str):
        return {"status": "rejected", "reason": source}
    if sturdy_survival_authority.get("status") != "ready":
        return deepcopy(dict(sturdy_survival_authority))
    predictive = base["predictive"]
    derived = deepcopy(dict(sturdy_survival_authority))
    derived.update({
        "source_branch_fingerprint": predictive["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(predictive["decision_owner"])),
        "source_sturdy_survival_authority": deepcopy(dict(sturdy_survival_authority)),
        "actor_neutral_root_predictive_binding": {
            "schema_version": root_predictive_authority["schema_version"],
            "root_action_id": root_predictive_authority["root_action_id"],
            "root_actor": deepcopy(dict(root_predictive_authority["root_actor"])),
            "root_target": deepcopy(dict(root_predictive_authority["root_target"])),
            "source_branch_fingerprint": root_predictive_authority["source_branch_fingerprint"],
            "predictive_source_branch_fingerprint": predictive["strategy_preview_fingerprint"],
        },
        "provenance": "runtime_d0_sturdy_survival_authority_through_actor_neutral_root_v1",
    })
    return derived


def freeze_runtime_d0_sturdy_survival_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    defender: Mapping[str, Any], attacker: Mapping[str, Any], action: Mapping[str, Any],
    move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind current, effective Sturdy readiness to one selected live action."""
    base = _base(strategy_d0, defender, attacker, action, move_metadata)
    if base is None:
        return _result("rejected", "invalid_sturdy_survival_request", {})
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"), base)
    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    row = _pokemon(state, defender)
    preview = strategy_d0.get("strategy_state", {}).get("active", {}).get(defender["side"])
    hp = _hp(preview)
    if row is None:
        return _result("rejected", "sturdy_defender_identity_mismatch", base)
    if hp is None:
        return _result("incomplete", "sturdy_hp_unknown", base)
    ability = _ability(row.get("current_ability"))
    payload = {**base, "current_hp": hp["current_hp"], "maximum_hp": hp["max_hp"], "current_ability_authority": ability}
    if ability["status"] == "unknown":
        return _result("incomplete", "sturdy_ability_unknown", payload)
    if ability["value"] != "sturdy":
        return _result("resolved", "known_non_sturdy_ability", payload, outcome="known_no_effect", sturdy_available=False, eligible=False)
    applicability = normalize_ability_applicability_context(
        state.get("ability_applicability_context") if isinstance(state, Mapping) else None,
        session_id=defender["session_id"], source=defender, ability_id="sturdy",
    )
    payload["sturdy_applicability_authority"] = applicability
    if applicability["status"] == "unknown":
        return _result("incomplete", "sturdy_applicability_unknown", payload)
    if applicability["status"] == "not_applicable":
        return _result("resolved", "sturdy_suppressed", payload, outcome="known_no_effect", sturdy_available=False, eligible=False)
    if hp["current_hp"] != hp["max_hp"] or hp["current_hp"] <= 1:
        return _result("resolved", "sturdy_hp_not_eligible", payload, outcome="known_no_effect", sturdy_available=True, eligible=False)
    return _result("ready", None, payload, outcome="available", sturdy_available=True, eligible=True)


def _base(d0: Any, defender: Any, attacker: Any, action: Any, metadata: Any) -> dict[str, Any] | None:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved" or not _owner(defender) or not _owner(attacker) or defender["side"] == attacker["side"]:
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or active.get(defender["side"]) != dict(defender) or active.get(attacker["side"]) != dict(attacker):
        return None
    if not isinstance(action, Mapping) or action.get("action_type") != "attack" or not isinstance(action.get("action_id"), str):
        return None
    move_id = metadata.get("move_id") if isinstance(metadata, Mapping) else None
    if not isinstance(move_id, str) or not move_id or action.get("identity", action.get("move_id")) != move_id:
        return None
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(d0["decision_owner"])),
        "defender": deepcopy(dict(defender)), "attacker": deepcopy(dict(attacker)),
        "action_id": action["action_id"], "move_id": move_id,
        "provenance": "runtime_d0_current_sturdy_survival_authority_v1",
    }


def _root_binding(d0: Any, root: Any) -> dict[str, Any] | str:
    if not isinstance(d0, Mapping) or d0.get("status") != "resolved":
        return "sturdy_root_source_d0_invalid"
    if not isinstance(root, Mapping) or root.get("status") != "resolved" or root.get("schema_version") != "detached-actor-neutral-root-predictive-authority-v1" or root.get("hypothetical") is not True:
        return "sturdy_actor_neutral_root_invalid"
    original = {
        "session_id": d0.get("session_id"),
        "source_runtime_fingerprint": d0.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": d0.get("strategy_preview_fingerprint"),
        "decision_owner": d0.get("decision_owner"),
    }
    if any(root.get(key) != value for key, value in original.items()):
        return "sturdy_actor_neutral_root_source_binding_mismatch"
    actor, target, predictive = root.get("root_actor"), root.get("root_target"), root.get("predictive_strategy_d0")
    if not _owner(actor) or not _owner(target) or actor["side"] == target["side"] or not isinstance(root.get("root_action_id"), str) or not isinstance(root.get("move_id"), str) or not root["move_id"]:
        return "sturdy_actor_neutral_root_identity_invalid"
    if not isinstance(predictive, Mapping) or predictive.get("status") != "resolved" or predictive.get("session_id") != root.get("session_id") or predictive.get("source_runtime_fingerprint") != root.get("source_runtime_fingerprint") or predictive.get("decision_owner") != actor or predictive.get("active_owners", {}).get(actor["side"]) != dict(actor) or predictive.get("active_owners", {}).get(target["side"]) != dict(target) or not isinstance(predictive.get("strategy_preview_fingerprint"), str):
        return "sturdy_actor_neutral_root_predictive_binding_invalid"
    return {"predictive": predictive, "actor": actor, "target": target, "action_id": root["root_action_id"], "move_id": root["move_id"], "original": original}


def _source_binding(authority: Any, root: Mapping[str, Any]) -> None | str:
    if not isinstance(authority, Mapping) or authority.get("schema_version") != SCHEMA_VERSION:
        return "sturdy_survival_authority_invalid"
    required = ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "defender", "attacker", "action_id", "move_id", "status")
    if any(key not in authority for key in required):
        return "sturdy_survival_authority_incomplete"
    if any(authority.get(key) != value for key, value in root["original"].items()):
        return "sturdy_actor_neutral_root_source_authority_binding_mismatch"
    if authority.get("defender") != root["target"] or authority.get("attacker") != root["actor"] or authority.get("action_id") != root["action_id"] or authority.get("move_id") != root["move_id"]:
        return "sturdy_actor_neutral_root_actor_recipient_binding_mismatch"
    return None


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    row = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return row if isinstance(row, Mapping) and row.get("pokemon_id") == owner["pokemon_id"] else None


def _hp(value: Any) -> dict[str, int] | None:
    if not isinstance(value, Mapping):
        return None
    hp, maximum, fainted = value.get("current_hp"), value.get("max_hp"), value.get("fainted")
    if isinstance(hp, int) and not isinstance(hp, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and maximum > 0 and 0 <= hp <= maximum and fainted is (hp == 0):
        return {"current_hp": hp, "max_hp": maximum}
    return None


def _ability(value: Any) -> dict[str, Any]:
    if isinstance(value, str) and value and not is_unknown_battle_fact(value):
        return {"status": "known", "value": value, "source": "runtime_current_ability", "trust": "runtime_current"}
    return {"status": "unknown", "value": None, "source": "unknown", "trust": "unknown"}


def _owner(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and isinstance(value.get("session_id"), str) and bool(value["session_id"]) and value.get("side") in {"self", "opponent"} and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _result(status: str, reason: str | None, base: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"status": status, **deepcopy(dict(base)), "reason": reason, **deepcopy(extra)}
