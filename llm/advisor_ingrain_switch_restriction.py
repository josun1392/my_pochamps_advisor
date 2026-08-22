"""Branch-bound Ingrain voluntary-switch restriction.

This is deliberately a narrow consumer of the existing persistent-effect
bundle and switch-permission pipeline.  It does not model other trapping
effects or forced switching.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from llm.advisor_ice_body_end_of_turn import _owners
from llm.advisor_persistent_effect_authority import persistent_effect_state
from llm.advisor_sandstorm_end_of_turn import _UNKNOWN, _item, _types
from llm.advisor_shadow_tag_switch_block import finalize_switch_candidates
from llm.advisor_switch_permission import normalize_switch_permission_context
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "detached-ingrain-switch-restriction-v1"
_PROVENANCE = "trusted_canonical_showdown_ingrain_switch_restriction"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")

# Pokemon Showdown's `ingrain` condition calls `pokemon.tryTrap()` from
# `onTrapPokemon`, and returns null from `onDragOut`.  `tryTrap()` honors the
# Ghost `trapped` immunity; Shed Shell later clears the trap flag in its own
# `onTrapPokemon` handler.  The raw upstream sources are retained here as
# bounded mechanics provenance, not as a runtime dependency.
CANONICAL_INGRAIN_SWITCH_AUTHORITY = {
    "source": "pokemon-showdown",
    "moves_source": "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts#ingrain",
    "pokemon_source": "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/sim/pokemon.ts#tryTrap",
    "typechart_source": "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/typechart.ts#ghost",
    "items_source": "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/items.ts#shedshell",
    "volatile": "ingrain",
    "voluntary_switch": "trapped_via_tryTrap",
    "forced_switch": "drag_out_cancelled",
    "exceptions": ("ghost_type", "shed_shell"),
}


def derive_ingrain_manual_switch_block(
    *, branch_state: Mapping[str, Any], source_branch_fingerprint: str, owner: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive only an exact Ingrain hard block for the current self active.

    `known_inactive` and an established canonical exception do not grant a
    switch: they merely establish that Ingrain itself is not the blocker.
    Unknown effect/type/item authority remains incomplete.
    """
    owners = _owners(branch_state)
    actual = fingerprint_transition_preview_state(branch_state)
    if (
        owners is None
        or actual != source_branch_fingerprint
        or not _exact_owner(owner)
        or dict(owner) != owners["self"]
    ):
        return _result("rejected", "stale_or_foreign_ingrain_switch_authority")

    row = persistent_effect_state(branch_state, "ingrain", "self", owner)
    if row is None:
        return _result("rejected", "stale_or_invalid_ingrain_persistent_authority")
    effect_state = row["state"]
    if effect_state == "unknown":
        return _result("incomplete", "ingrain_persistent_effect_unknown")
    if effect_state == "known_inactive":
        return _resolved(owner, source_branch_fingerprint, effect_state, "not_established")

    current_types = _types(branch_state, "self")
    if current_types is None:
        return _result("incomplete", "ingrain_switch_current_type_authority")
    if "ghost" in current_types:
        return _resolved(owner, source_branch_fingerprint, effect_state, "exception_applies", "ghost_type")

    item = _item(branch_state, "self")
    if item is _UNKNOWN:
        return _result("incomplete", "ingrain_switch_current_item_authority")
    if item == "shed-shell":
        return _resolved(owner, source_branch_fingerprint, effect_state, "exception_applies", "shed_shell")
    return _resolved(owner, source_branch_fingerprint, effect_state, "confirmed_blocked")


def finalize_ingrain_manual_switch_candidates(
    *, base_candidates: Sequence[Mapping[str, Any]], manual_permission: Mapping[str, Any],
    branch_state: Mapping[str, Any], source_branch_fingerprint: str, owner: Mapping[str, Any],
) -> dict[str, Any]:
    """Finalize normal manual candidates with the exact Ingrain hard blocker."""
    block = derive_ingrain_manual_switch_block(
        branch_state=branch_state,
        source_branch_fingerprint=source_branch_fingerprint,
        owner=owner,
    )
    if block.get("status") != "resolved":
        return block
    normalized = normalize_switch_permission_context(
        manual_permission,
        session_id=owner["session_id"],
        active_slot_index=owner["slot_index"],
        active_pokemon_id=owner["pokemon_id"],
    )
    blocker = {"state": block["block_state"]}
    return {
        "status": "resolved",
        "source_branch_fingerprint": source_branch_fingerprint,
        "owner": deepcopy(dict(owner)),
        "ingrain_switch_restriction": block,
        "manual_permission": normalized,
        "switch_candidates": finalize_switch_candidates(
            base_candidates,
            manual_permission=normalized,
            blocker=blocker,
        ),
    }


def _exact_owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str)
        and bool(value["session_id"])
        and value.get("side") == "self"
        and isinstance(value.get("slot_index"), int)
        and not isinstance(value["slot_index"], bool)
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str)
        and bool(value["pokemon_id"])
    )


def _resolved(owner: Mapping[str, Any], fingerprint: str, effect_state: str, block_state: str, exception: str | None = None) -> dict[str, Any]:
    result = {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "session_id": owner["session_id"],
        "source_branch_fingerprint": fingerprint,
        "owner": deepcopy(dict(owner)),
        "ingrain_state": effect_state,
        "block_state": block_state,
        "provenance": _PROVENANCE,
        "canonical_authority": deepcopy(CANONICAL_INGRAIN_SWITCH_AUTHORITY),
    }
    if exception is not None:
        result["exception"] = exception
    return result


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
