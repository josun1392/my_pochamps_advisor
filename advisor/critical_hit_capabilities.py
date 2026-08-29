"""Strict detached capability classification for bounded Gen 9 critical hits."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.damage.crit import is_crit_blocked, move_crit_rule, resolve_crit_stage


SCHEMA_VERSION = "critical-hit-capability-resolution-v1"
CATALOG_VERSION = "critical-hit-capability-catalog-v1"
# These are canonical ordinary damaging moves whose critical-hit behavior is
# the Gen 9 base rule.  Move-specific high-/always-critical rules remain
# delegated to ``move_crit_rule`` below.
_BASE_MOVE_IDS = frozenset({
    "tackle", "water-gun", "thunderbolt", "facade", "sparkling-aria",
    # Rock Slide is the explicitly scoped direct-damage move for the first
    # frozen-recipient doubles execution graph.
    "rock-slide",
    # These moves already have bounded predictive secondary/stage mechanics.
    # Keeping this list explicit makes their ordinary Gen 9 crit rule usable
    # without turning uncatalogued attacks into a generic supported family.
    "metal-claw", "shadow-ball", "acid-spray", "close-combat", "flame-charge",
    "iron-head",
    # Fixed-two-hit moves admitted by the detached per-hit execution
    # authority.  Their normal Gen 9 critical rule is the ordinary base rule;
    # the authority still keeps each hit's eventual critical roll distinct.
    "double-hit", "double-kick",
    # Ordinary canonical 2--5-hit moves admitted by the detached hit-count
    # authority.  Each eventual hit keeps an independent ordinary crit roll.
    "bullet-seed", "rock-blast",
    # Population Bomb has the same canonical ordinary critical rule on every
    # landed attempt. Its independent accuracy sequence is owned separately.
    "population-bomb",
    # Canonical escalating three-hit moves admitted by the strict execution
    # authority.  Each landed hit retains the ordinary Gen 9 crit rule.
    "triple-axel", "triple-kick",
})
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_SOURCE_STATUSES = frozenset({"known", "known_absent", "unknown"})
_SUPPORTED_ATTACKER_ABILITIES = frozenset({"pressure", "super-luck", "merciless", "sniper", "guts", "skill-link"})
_SUPPORTED_DEFENDER_ABILITIES = frozenset({
    "pressure", "intimidate", "drizzle", "drought", "sand-stream", "snow-warning",
    "battle-armor", "shell-armor", "guts", "sturdy",
})
_SUPPORTED_ATTACKER_ITEMS = frozenset({"scope-lens", "razor-claw", "loaded-dice"})
_POISONED = frozenset({"poison", "poisoned", "toxic", "badly-poisoned"})


def resolve_critical_hit_capabilities(*, move: Mapping[str, Any], source_authority: Mapping[str, Any],
    critical_state_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify a bounded crit family without calculating its final probability.

    The resolver accepts only detached authority.  It calls the native crit
    engine after every source that can affect the selected family is exact.
    """
    context = _context(move, critical_state_authority)
    if context is None or not isinstance(source_authority, Mapping):
        return _result("rejected", "invalid_critical_hit_capability_request")
    move_rule = _move_rule(context["move_id"])
    base = _base(context, move_rule)
    if move_rule == "unsupported":
        return {**base, "status": "unsupported", "reason": "move_not_in_supported_critical_hit_catalog", "ledger": (_row("move_rule", "unsupported", source_value=context["move_id"]),)}

    sources = _sources(source_authority)
    if sources is None:
        return _result("rejected", "invalid_critical_hit_source_authority")
    volatile = _critical_state(context, critical_state_authority)
    if volatile is None:
        return _result("rejected", "invalid_current_critical_state_authority")

    ledger: list[dict[str, Any]] = [_row("move_rule", "applicable", rule_id=move_rule)]
    ability = _attacker_ability(sources["attacker_ability"], sources["target_condition"], ledger)
    if ability["status"] != "resolved":
        return {**base, **ability, "ledger": tuple(ledger)}
    defender = _defender_ability(sources["defender_ability"], ledger)
    if defender["status"] != "resolved":
        return {**base, **defender, "ledger": tuple(ledger)}
    item = _attacker_item(sources["attacker_item"], ledger)
    if item["status"] != "resolved":
        return {**base, **item, "ledger": tuple(ledger)}
    volatiles = _volatiles(volatile["attacker"], sources["attacker_types"], ledger)
    if volatiles["status"] != "resolved":
        return {**base, **volatiles, "ledger": tuple(ledger)}
    blocker = _blocker(volatile["target"], defender["value"], ledger)
    if blocker["status"] != "resolved":
        return {**base, **blocker, "ledger": tuple(ledger)}

    attacker_state = {
        "ability": ability["value"], "item": item["value"],
        "types": volatiles["types"], "volatiles": volatiles["values"],
    }
    defender_state = {"ability": defender["value"], "status": ability["target_condition"]}
    stage = resolve_crit_stage(attacker_state, {"move_id": context["move_id"]}, defender_state)
    blocked = is_crit_blocked(defender_state, {"defender_lucky_chant": blocker["value"]})
    return {
        **base, "status": "resolved", "ledger": tuple(ledger),
        "crit_stage": stage,
        "crit_blocker": {"status": "known_present" if blocked else "known_absent", "source": "canonical_gen9_critical_hit_engine"},
        "damage_compatibility": {"status": "supported", "critical_damage_engine": "advisor.damage.crit", "attacker_sniper": ability["value"] == "sniper"},
        "provenance": "detached_critical_hit_capability_resolver_v1",
    }


def _context(move: Any, state: Any) -> dict[str, Any] | None:
    if not isinstance(move, Mapping) or not isinstance(state, Mapping):
        return None
    move_id = move.get("move_id")
    if not isinstance(move_id, str) or not move_id:
        return None
    attacker, target = state.get("attacker"), state.get("target")
    if not _critical_authority(attacker) or not _critical_authority(target):
        return None
    if not _same_binding(attacker, target) or attacker["owner"].get("side") == target["owner"].get("side"):
        return None
    return {
        "move_id": move_id, "session_id": attacker["session_id"],
        "source_runtime_fingerprint": attacker["source_runtime_fingerprint"],
        "source_branch_fingerprint": attacker["source_branch_fingerprint"],
        "attacker": deepcopy(dict(attacker["owner"])), "target": deepcopy(dict(target["owner"])),
    }


def _critical_authority(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") == "resolved" and value.get("schema_version") == "runtime-current-critical-state-authority-v1" and _binding(value.get("session_id"), value.get("source_runtime_fingerprint"), value.get("source_branch_fingerprint"), value.get("owner")) and isinstance(value.get("crit_volatiles"), Mapping) and isinstance(value.get("lucky_chant"), Mapping)


def _binding(session: Any, runtime: Any, branch: Any, owner: Any) -> bool:
    return isinstance(session, str) and bool(session) and isinstance(runtime, str) and bool(runtime) and isinstance(branch, str) and bool(branch) and isinstance(owner, Mapping) and set(owner) == set(_OWNER_KEYS) and owner.get("session_id") == session and owner.get("side") in {"self", "opponent"} and isinstance(owner.get("slot_index"), int) and not isinstance(owner.get("slot_index"), bool) and owner["slot_index"] >= 0 and isinstance(owner.get("pokemon_id"), str) and bool(owner["pokemon_id"])


def _same_binding(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(left.get(key) == right.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint"))


def _move_rule(move_id: str) -> str:
    rule = move_crit_rule(move_id)
    if rule in {"high-crit", "always-crit"}:
        return rule
    return "base" if move_id in _BASE_MOVE_IDS else "unsupported"


def _sources(value: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    required = ("attacker_ability", "defender_ability", "attacker_item")
    if not all(key in value for key in required):
        return None
    result = {key: _source(value[key]) for key in required}
    result["target_condition"] = _source(value.get("target_condition", {"status": "unknown"}))
    result["attacker_types"] = _source(value.get("attacker_types", {"status": "unknown"}), sequence=True)
    return result if all(item is not None for item in result.values()) else None


def _source(value: Any, *, sequence: bool = False) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("status") not in _SOURCE_STATUSES:
        return None
    status = value["status"]
    if status != "known":
        if sequence and status != "unknown":
            return None
        return {"status": status} if set(value) == {"status"} else None
    raw = value.get("value")
    valid = isinstance(raw, (list, tuple)) and all(isinstance(item, str) and item for item in raw) if sequence else isinstance(raw, str) and bool(raw)
    return {"status": status, "value": tuple(raw) if sequence else raw} if valid and set(value) == {"status", "value"} else None


def _critical_state(context: Mapping[str, Any], value: Mapping[str, Any]) -> dict[str, Mapping[str, Any]] | None:
    attacker, target = value["attacker"], value["target"]
    own = attacker.get("crit_volatiles")
    lucky = target.get("lucky_chant")
    binding = (context["session_id"], context["source_runtime_fingerprint"], context["source_branch_fingerprint"])
    if not isinstance(own, Mapping) or own.get("status") != "resolved" or own.get("schema_version") != "runtime-current-crit-volatile-authority-v1" or own.get("owner") != context["attacker"] or tuple(own.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) != binding or not isinstance(lucky, Mapping) or lucky.get("status") != "resolved" or lucky.get("schema_version") != "runtime-current-lucky-chant-authority-v1" or lucky.get("side") != context["target"]["side"] or tuple(lucky.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) != binding:
        return None
    states = own.get("volatiles")
    lucky_state = lucky.get("lucky_chant")
    if not isinstance(states, Mapping) or set(states) != {"focus-energy", "lansat", "dragon-cheer"} or not _state(lucky_state):
        return None
    if any(not _state(states.get(key)) for key in states):
        return None
    return {"attacker": states, "target": lucky_state}


def _state(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("status") in {"known_present", "known_absent", "unknown"}


def _attacker_ability(source: Mapping[str, Any], condition: Mapping[str, Any], ledger: list[dict[str, Any]]) -> dict[str, Any]:
    if source["status"] == "unknown":
        ledger.append(_row("attacker_ability", "unknown")); return _incomplete("attacker_ability_unknown")
    if source["status"] == "known_absent":
        ledger.append(_row("attacker_ability", "known_neutral", reason="proven_ability_absent")); return _resolved(None, None)
    ability = source["value"]
    if ability not in _SUPPORTED_ATTACKER_ABILITIES:
        ledger.append(_row("attacker_ability", "unsupported", source_value=ability)); return _unsupported("attacker_ability_not_in_supported_critical_hit_catalog")
    if ability != "merciless":
        state = "applicable" if ability in {"super-luck", "sniper"} else "known_neutral"
        ledger.append(_row("attacker_ability", state, source_value=ability)); return _resolved(ability, None)
    if condition["status"] == "unknown":
        ledger.extend((_row("attacker_ability", "applicable", source_value=ability), _row("target_condition", "unknown"))); return _incomplete("merciless_target_condition_unknown")
    poisoned = condition["status"] == "known" and condition["value"] in _POISONED
    ledger.extend((_row("attacker_ability", "applicable" if poisoned else "known_neutral", source_value=ability), _row("target_condition", "applicable" if poisoned else "known_neutral")))
    return _resolved(ability, condition.get("value") if condition["status"] == "known" else None)


def _defender_ability(source: Mapping[str, Any], ledger: list[dict[str, Any]]) -> dict[str, Any]:
    if source["status"] == "unknown":
        ledger.append(_row("defender_ability", "unknown")); return _incomplete("defender_ability_unknown")
    if source["status"] == "known_absent":
        ledger.append(_row("defender_ability", "known_neutral", reason="proven_ability_absent")); return _resolved(None)
    ability = source["value"]
    if ability not in _SUPPORTED_DEFENDER_ABILITIES:
        ledger.append(_row("defender_ability", "unsupported", source_value=ability)); return _unsupported("defender_ability_not_in_supported_critical_hit_catalog")
    ledger.append(_row("defender_ability", "applicable" if ability in {"battle-armor", "shell-armor"} else "known_neutral", source_value=ability))
    return _resolved(ability)


def _attacker_item(source: Mapping[str, Any], ledger: list[dict[str, Any]]) -> dict[str, Any]:
    if source["status"] == "unknown":
        ledger.append(_row("attacker_item", "unknown")); return _incomplete("attacker_item_unknown")
    if source["status"] == "known_absent":
        ledger.append(_row("attacker_item", "known_neutral", reason="proven_item_absent")); return _resolved(None)
    item = source["value"]
    if item not in _SUPPORTED_ATTACKER_ITEMS:
        ledger.append(_row("attacker_item", "unsupported", source_value=item)); return _unsupported("attacker_item_not_in_supported_critical_hit_catalog")
    ledger.append(_row("attacker_item", "applicable", source_value=item)); return _resolved(item)


def _volatiles(states: Mapping[str, Any], types: Mapping[str, Any], ledger: list[dict[str, Any]]) -> dict[str, Any]:
    values = []
    for name in ("focus-energy", "lansat", "dragon-cheer"):
        state = states[name]["status"]
        if state == "unknown":
            ledger.append(_row(name, "unknown")); return _incomplete(f"{name}_unknown")
        if state == "known_present": values.append(name); ledger.append(_row(name, "applicable"))
        else: ledger.append(_row(name, "known_neutral", reason="proven_volatile_absent"))
    resolved_types: tuple[str, ...] = ()
    if "dragon-cheer" in values:
        if types["status"] == "unknown":
            ledger.append(_row("attacker_types", "unknown")); return _incomplete("dragon_cheer_attacker_types_unknown")
        resolved_types = types["value"]
        ledger.append(_row("attacker_types", "applicable"))
    return {"status": "resolved", "values": values, "types": resolved_types}


def _blocker(state: Mapping[str, Any], defender_ability: str | None, ledger: list[dict[str, Any]]) -> dict[str, Any]:
    if state["status"] == "unknown":
        ledger.append(_row("target_lucky_chant", "unknown")); return _incomplete("target_lucky_chant_unknown")
    present = state["status"] == "known_present"
    ledger.append(_row("target_lucky_chant", "applicable" if present else "known_neutral", reason=None if present else "proven_lucky_chant_absent"))
    return _resolved(present)


def _base(context: Mapping[str, Any], move_rule: str) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "catalog_version": CATALOG_VERSION, "session_id": context["session_id"], "source_runtime_fingerprint": context["source_runtime_fingerprint"], "source_branch_fingerprint": context["source_branch_fingerprint"], "attacker": deepcopy(context["attacker"]), "target": deepcopy(context["target"]), "move_id": context["move_id"], "move_rule": move_rule}


def _row(slot: str, state: str, *, rule_id: str | None = None, reason: str | None = None, source_value: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"slot": slot, "state": state}
    if rule_id is not None: result["rule_id"] = rule_id
    if reason is not None: result["reason"] = reason
    if source_value is not None: result["source_value"] = source_value
    return result


def _resolved(value: Any, target_condition: Any = None) -> dict[str, Any]:
    return {"status": "resolved", "value": value, "target_condition": target_condition, "types": value if isinstance(value, tuple) else (), "values": value if isinstance(value, list) else []}


def _incomplete(reason: str) -> dict[str, Any]: return {"status": "incomplete", "reason": reason}
def _unsupported(reason: str) -> dict[str, Any]: return {"status": "unsupported", "reason": reason}
def _result(status: str, reason: str) -> dict[str, Any]: return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}
