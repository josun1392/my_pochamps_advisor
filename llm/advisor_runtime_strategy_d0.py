"""Runtime-owned, one-way D0 authority for detached strategy previews.

``battle-state-v1`` remains the mutable runtime source of truth.  This module
only freezes a detached ``deterministic-transition-preview-v1`` view and keeps
the originating reducer fingerprint alongside its preview fingerprint.  It
does not make UI/recommendation projections into battle-state owners.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from llm.advisor_current_action_authority import freeze_current_action_authority
from llm.advisor_current_stage_authority import (
    native_damage_stage_authority, project_current_stage_authority,
    strict_hit_stage_authority,
)
from llm.advisor_current_critical_state_authority import (
    project_current_crit_volatile_authority,
    project_current_lucky_chant_authority,
)
from llm.advisor_current_condition_authority import project_current_condition_authority
from llm.advisor_battle_state_context import build_deterministic_hit_chance_assessment
from llm.advisor_ability_interaction_authority import (
    normalize_ability_applicability_context,
    normalize_ability_interaction_context,
)
from advisor.hit_modifier_capabilities import resolve_hit_modifier_capabilities
from advisor.probabilistic_self_stage_effect_capabilities import (
    resolve_probabilistic_self_stage_effect_capability,
)
from advisor.probabilistic_target_stage_effect_capabilities import (
    resolve_probabilistic_target_stage_effect_capability,
)
from advisor.probabilistic_target_status_effect_capabilities import (
    resolve_probabilistic_target_status_effect_capability,
)
from advisor.critical_hit_capabilities import resolve_critical_hit_capabilities
from advisor.strict_critical_hit_probability import assess_strict_critical_hit_probability
from advisor.strict_hit_probability import assess_strict_deterministic_hit_probability
from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_predictive_normal_formula_interval import normal_formula_eligibility
from llm.advisor_reducer_state_model import (
    STATE_MODEL_VERSION,
    is_unknown_battle_fact,
    state_fingerprint,
    validate_battle_state_unknown_markers,
)
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from llm.advisor_substitute import substitute_state


SCHEMA = "deterministic-runtime-strategy-d0-v1"
PREVIEW_SCHEMA = "deterministic-transition-preview-v1"
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_NATIVE_STAT_KEYS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")
_NATIVE_STAGE_KEYS = ("attack", "defense", "special-attack", "special-defense", "speed")


def freeze_runtime_strategy_d0(*, runtime_snapshot: Mapping[str, Any], decision_owner: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze a detached strategy D0 from one exact runtime snapshot.

    Unknown reducer facts are deliberately not replaced with strategy defaults.
    They remain untracked in the preview and cause downstream mechanics to fail
    closed when those mechanics require exact state.
    """
    state, session_id, runtime_fingerprint = _runtime_snapshot(runtime_snapshot)
    if state is None or not _owner(decision_owner) or decision_owner.get("session_id") != session_id:
        return _result("rejected", "invalid_runtime_d0_authority")
    owners = _active_owners(state, session_id)
    if owners is None or owners.get(decision_owner["side"]) != dict(decision_owner):
        return _result("rejected", "runtime_decision_owner_mismatch")
    preview = {
        "schema_version": PREVIEW_SCHEMA,
        "active": {
            side: _preview_active(state, side, owner)
            for side, owner in owners.items()
        },
        "current_state": {
            "current_state_session_id": session_id,
            # This is provenance only.  Existing mechanics do not consume it as
            # exact current-state authority, so missing conversion adapters stay
            # unknown instead of becoming neutral defaults.
            "runtime_strategy_d0_authority": _runtime_authority_summary(state),
        },
    }
    # The canonical reducer representation already carries its own owner rows.
    # Absence is intentionally preserved as legacy/untracked, not inactive.
    if isinstance(state.get("substitute_state_context"), Mapping):
        preview["substitute_state_context"] = deepcopy(dict(state["substitute_state_context"]))
    preview_fingerprint = fingerprint_transition_preview_state(preview)
    if not isinstance(preview_fingerprint, str):
        return _result("rejected", "unserializable_strategy_d0")
    result = {
        "status": "resolved",
        "schema_version": SCHEMA,
        "session_id": session_id,
        "source_runtime_fingerprint": runtime_fingerprint,
        "strategy_preview_fingerprint": preview_fingerprint,
        "decision_owner": deepcopy(dict(decision_owner)),
        "active_owners": deepcopy(owners),
        "strategy_state": deepcopy(preview),
        "provenance": "runtime_battle_state_v1_to_detached_strategy_d0_v1",
    }
    result["current_stage_authority"] = {
        side: project_current_stage_authority(
            session_id=session_id, source_runtime_fingerprint=runtime_fingerprint,
            source_branch_fingerprint=preview_fingerprint, owner=owner,
            current_stages=_roster(state, side).get(owner["slot_index"], {}).get("stat_stages"),
        ) for side, owner in owners.items()
    }
    result["current_condition_authority"] = {
        side: project_current_condition_authority(
            session_id=session_id, source_runtime_fingerprint=runtime_fingerprint,
            source_branch_fingerprint=preview_fingerprint, owner=owner,
            current_condition=_roster(state, side).get(owner["slot_index"], {}).get("condition"),
            current_condition_provenance=_roster(state, side).get(owner["slot_index"], {}).get("condition_provenance"),
        ) for side, owner in owners.items()
    }
    result["current_critical_state_authority"] = {
        "volatiles": {
            side: project_current_crit_volatile_authority(
                session_id=session_id, source_runtime_fingerprint=runtime_fingerprint,
                source_branch_fingerprint=preview_fingerprint, owner=owner,
                current_crit_volatiles=_runtime_crit_volatiles_exact(_roster(state, side).get(owner["slot_index"], {})),
            ) for side, owner in owners.items()
        },
        "lucky_chant": {
            side: project_current_lucky_chant_authority(
                session_id=session_id, source_runtime_fingerprint=runtime_fingerprint,
                source_branch_fingerprint=preview_fingerprint, side=side,
                current_side_conditions=_runtime_side_conditions_exact(state.get(f"{side}_side")),
            ) for side in owners
        },
    }
    return result


def resolve_runtime_strategy_decision_owner(*, runtime_snapshot: Mapping[str, Any], side: str = "self") -> dict[str, Any]:
    """Return the canonical active owner for one runtime side, if exact."""
    state, session_id, _fingerprint = _runtime_snapshot(runtime_snapshot)
    owners = _active_owners(state, session_id) if state is not None and session_id is not None else None
    if side not in {"self", "opponent"} or owners is None:
        return _result("rejected", "runtime_decision_owner_unavailable")
    return {"status": "resolved", "decision_owner": deepcopy(owners[side])}


def freeze_runtime_current_stage_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    """Return the detached seven-stage authority for one exact active owner."""
    if not _valid_d0(strategy_d0) or not _owner(owner) or strategy_d0.get("active_owners", {}).get(owner.get("side")) != dict(owner):
        return _result("rejected", "runtime_current_stage_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current": return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    authority = strategy_d0.get("current_stage_authority", {}).get(owner["side"])
    if not isinstance(authority, Mapping) or authority.get("owner") != dict(owner):
        return _result("rejected", "runtime_current_stage_authority_unavailable")
    return deepcopy(dict(authority))


def freeze_runtime_current_condition_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    """Return the detached strict major-condition authority for one active owner."""
    if not _valid_d0(strategy_d0) or not _owner(owner) or strategy_d0.get("active_owners", {}).get(owner.get("side")) != dict(owner):
        return _result("rejected", "runtime_current_condition_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    authority = strategy_d0.get("current_condition_authority", {}).get(owner["side"])
    if not isinstance(authority, Mapping) or authority.get("owner") != dict(owner):
        return _result("rejected", "runtime_current_condition_authority_unavailable")
    return deepcopy(dict(authority))


def freeze_runtime_current_critical_state_authority(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    """Return one detached current crit-state view for the exact active owner."""
    if not _valid_d0(strategy_d0) or not _owner(owner) or strategy_d0.get("active_owners", {}).get(owner.get("side")) != dict(owner):
        return _result("rejected", "runtime_current_critical_state_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    current = strategy_d0.get("current_critical_state_authority")
    if not isinstance(current, Mapping):
        return _result("rejected", "runtime_current_critical_state_authority_unavailable")
    volatile = current.get("volatiles", {}).get(owner["side"]) if isinstance(current.get("volatiles"), Mapping) else None
    lucky_chant = current.get("lucky_chant", {}).get(owner["side"]) if isinstance(current.get("lucky_chant"), Mapping) else None
    if not isinstance(volatile, Mapping) or volatile.get("owner") != dict(owner) or not isinstance(lucky_chant, Mapping) or lucky_chant.get("side") != owner["side"]:
        return _result("rejected", "runtime_current_critical_state_authority_unavailable")
    return {
        "status": "resolved", "schema_version": "runtime-current-critical-state-authority-v1",
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "owner": deepcopy(dict(owner)),
        "crit_volatiles": deepcopy(dict(volatile)), "lucky_chant": deepcopy(dict(lucky_chant)),
        "provenance": "runtime_battle_state_v1_to_detached_current_critical_state_authority_v1",
    }


def freeze_runtime_d0_critical_hit_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind exact current facts to the detached crit capability resolver."""
    move_id = move_metadata.get("move_id") if isinstance(move_metadata, Mapping) else None
    active = strategy_d0.get("active_owners") if isinstance(strategy_d0, Mapping) else None
    if (
        not _valid_d0(strategy_d0) or not isinstance(move_id, str) or not move_id
        or not _owner(attacker) or not _owner(target) or attacker != strategy_d0["decision_owner"]
        or not isinstance(active, Mapping) or active.get(attacker["side"]) != dict(attacker)
        or active.get(target["side"]) != dict(target) or attacker["side"] == target["side"]
    ):
        return _result("rejected", "runtime_critical_hit_identity_or_move_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    raw_attacker = _roster(state, attacker["side"]).get(attacker["slot_index"])
    raw_target = _roster(state, target["side"]).get(target["slot_index"])
    if not isinstance(raw_attacker, Mapping) or not isinstance(raw_target, Mapping) or not _same_runtime_owner(raw_attacker, attacker) or not _same_runtime_owner(raw_target, target):
        return _result("rejected", "runtime_critical_hit_identity_mismatch")
    attacker_critical = freeze_runtime_current_critical_state_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=attacker)
    target_critical = freeze_runtime_current_critical_state_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
    sources = _runtime_critical_hit_sources(raw_attacker=raw_attacker, raw_target=raw_target)
    capability = resolve_critical_hit_capabilities(
        move={"move_id": move_id}, source_authority=sources,
        critical_state_authority={"attacker": attacker_critical, "target": target_critical},
    )
    return {
        "status": capability["status"], "schema_version": "runtime-d0-critical-hit-authority-v1",
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move": {"move_id": move_id},
        "source_authority": deepcopy(sources),
        "current_critical_state_authority": {"attacker": deepcopy(attacker_critical), "target": deepcopy(target_critical)},
        "capability_resolution": deepcopy(capability),
        "provenance": "runtime_battle_state_v1_to_detached_critical_hit_authority_v1",
        **({"reason": capability["reason"]} if capability.get("status") != "resolved" and isinstance(capability.get("reason"), str) else {}),
    }


def build_runtime_d0_strict_critical_hit_probability_assessment(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Return strict crit probability from the existing D0 authority boundary."""
    authority = freeze_runtime_d0_critical_hit_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=attacker, target=target, move_metadata=move_metadata,
    )
    if authority.get("status") == "rejected":
        return {"status": "rejected", "schema_version": "strict-critical-hit-probability-v1", "reason": authority.get("reason", "runtime_critical_hit_authority_rejected")}
    return assess_strict_critical_hit_probability(critical_hit_authority=authority)


def build_runtime_d0_strict_hit_chance_assessment(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], selected_move: Mapping[str, Any]) -> dict[str, Any]:
    """Strict runtime boundary around the legacy neutral-default hit helper."""
    if not _valid_d0(strategy_d0) or not _owner(attacker) or not _owner(target) or attacker != strategy_d0.get("decision_owner") or attacker.get("side") == target.get("side"):
        return _result("rejected", "runtime_hit_stage_identity_mismatch")
    if isinstance(selected_move, Mapping) and selected_move.get("always_hit") is True:
        return {"status": "resolved", "schema_version": "runtime-d0-strict-hit-chance-v1", "stage_authority": {"status": "not_required", "reason": "move_always_hits"}, "assessment": build_deterministic_hit_chance_assessment(selected_move, None)}
    attacker_authority = freeze_runtime_current_stage_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=attacker)
    target_authority = freeze_runtime_current_stage_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
    stages = strict_hit_stage_authority(attacker_authority=attacker_authority, target_authority=target_authority)
    if stages.get("status") != "resolved":
        return {"status": stages.get("status", "incomplete"), "schema_version": "runtime-d0-strict-hit-chance-v1", "reason": stages.get("reason", "hit_stage_authority_incomplete"), "missing_authority": deepcopy(stages.get("missing_authority", []))}
    assessment = build_deterministic_hit_chance_assessment(selected_move, stages["stat_stage_context"])
    return {"status": "resolved", "schema_version": "runtime-d0-strict-hit-chance-v1", "stage_authority": stages, "assessment": assessment}


def freeze_runtime_d0_hit_modifier_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze resolver inputs for the supported Hustle hit-modifier family."""
    move = _hit_modifier_move(move_metadata)
    active = strategy_d0.get("active_owners") if isinstance(strategy_d0, Mapping) else None
    if (
        not _valid_d0(strategy_d0) or move is None or not _owner(attacker) or not _owner(target)
        or attacker != strategy_d0["decision_owner"] or not isinstance(active, Mapping)
        or active.get(attacker["side"]) != dict(attacker) or active.get(target["side"]) != dict(target)
        or attacker["side"] == target["side"]
    ):
        return _result("rejected", "runtime_hit_modifier_identity_or_move_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current": return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    raw_attacker = _roster(state, attacker["side"]).get(attacker["slot_index"])
    raw_target = _roster(state, target["side"]).get(target["slot_index"])
    if not isinstance(raw_attacker, Mapping) or not isinstance(raw_target, Mapping) or not _same_runtime_owner(raw_attacker, attacker) or not _same_runtime_owner(raw_target, target):
        return _result("rejected", "runtime_hit_modifier_identity_mismatch")
    ability_authority = _runtime_hustle_ability_authority(state=state, raw_attacker=raw_attacker, attacker=attacker)
    capability = resolve_hit_modifier_capabilities(move=move, source_authority={"attacker_ability": ability_authority})
    attacker_stages = freeze_runtime_current_stage_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=attacker)
    target_stages = freeze_runtime_current_stage_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target)
    stage_authority = strict_hit_stage_authority(attacker_authority=attacker_stages, target_authority=target_stages)
    return {
        "status": capability["status"], "schema_version": "runtime-d0-hit-modifier-authority-v1",
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)),
        "move": deepcopy(move), "source_authority": {"attacker_ability": deepcopy(ability_authority)},
        "capability_resolution": deepcopy(capability), "strict_stage_authority": deepcopy(stage_authority),
        "provenance": "runtime_battle_state_v1_hit_modifier_authority_v1",
    }


def freeze_runtime_d0_probabilistic_self_stage_effect_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze exact D0 facts for catalogued self-owned stage secondaries.

    This adapter does not predict a successful hit or apply a stage delta.  It
    only joins the current runtime ability/applicability and Attack-stage
    authorities to the pure capability resolver for a later hit-leaf consumer.
    """
    move_id = move_metadata.get("move_id") if isinstance(move_metadata, Mapping) else None
    active = strategy_d0.get("active_owners") if isinstance(strategy_d0, Mapping) else None
    if (
        not _valid_d0(strategy_d0) or not isinstance(move_id, str) or not move_id
        or not _owner(attacker) or not _owner(target) or attacker != strategy_d0["decision_owner"]
        or not isinstance(active, Mapping) or active.get(attacker["side"]) != dict(attacker)
        or active.get(target["side"]) != dict(target) or attacker["side"] == target["side"]
    ):
        return _result("rejected", "runtime_probabilistic_self_stage_identity_or_move_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    raw_attacker = _roster(state, attacker["side"]).get(attacker["slot_index"])
    raw_target = _roster(state, target["side"]).get(target["slot_index"])
    if not isinstance(raw_attacker, Mapping) or not isinstance(raw_target, Mapping) or not _same_runtime_owner(raw_attacker, attacker) or not _same_runtime_owner(raw_target, target):
        return _result("rejected", "runtime_probabilistic_self_stage_identity_mismatch")
    ability_authority = _runtime_probabilistic_self_stage_ability_authority(
        state=state, raw_attacker=raw_attacker, attacker=attacker,
    )
    capability = resolve_probabilistic_self_stage_effect_capability(
        move=move_metadata, source_authority={"attacker_ability": ability_authority},
    )
    stage_authority = freeze_runtime_current_stage_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=attacker,
    )
    status, reason = capability.get("status", "rejected"), capability.get("reason")
    attack_stage = None
    if stage_authority.get("status") == "rejected":
        status, reason = "rejected", stage_authority.get("reason", "runtime_current_stage_authority_unavailable")
    elif not _known_current_stage(stage_authority, "attack"):
        if status == "resolved":
            status, reason = "incomplete", "attacker_attack_stage_unknown"
    else:
        attack_stage = deepcopy(stage_authority["stages"]["attack"])
    result = {
        "status": status,
        "schema_version": "runtime-d0-probabilistic-self-stage-effect-authority-v1",
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)),
        "target": deepcopy(dict(target)),
        "move": deepcopy(dict(move_metadata)),
        "source_authority": {"attacker_ability": deepcopy(ability_authority)},
        "capability_resolution": deepcopy(capability),
        "current_stage_authority": deepcopy(stage_authority),
        "current_attack_stage": attack_stage,
        "provenance": "runtime_battle_state_v1_to_detached_probabilistic_self_stage_effect_authority_v1",
    }
    if status != "resolved" and isinstance(reason, str):
        result["reason"] = reason
    return result


def freeze_runtime_d0_probabilistic_target_stage_effect_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze exact D0 facts for catalogued target-owned stage secondaries.

    The adapter deliberately does not decide whether the target survived a
    damage roll or apply a hypothetical drop.  Those are hit-leaf concerns;
    this handoff only joins current source facts to the pure resolver.
    """
    move_id = move_metadata.get("move_id") if isinstance(move_metadata, Mapping) else None
    active = strategy_d0.get("active_owners") if isinstance(strategy_d0, Mapping) else None
    if (
        not _valid_d0(strategy_d0) or not isinstance(move_id, str) or not move_id
        or not _owner(attacker) or not _owner(target) or attacker != strategy_d0["decision_owner"]
        or not isinstance(active, Mapping) or active.get(attacker["side"]) != dict(attacker)
        or active.get(target["side"]) != dict(target) or attacker["side"] == target["side"]
    ):
        return _result("rejected", "runtime_probabilistic_target_stage_identity_or_move_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    raw_attacker = _roster(state, attacker["side"]).get(attacker["slot_index"])
    raw_target = _roster(state, target["side"]).get(target["slot_index"])
    if not isinstance(raw_attacker, Mapping) or not isinstance(raw_target, Mapping) or not _same_runtime_owner(raw_attacker, attacker) or not _same_runtime_owner(raw_target, target):
        return _result("rejected", "runtime_probabilistic_target_stage_identity_mismatch")
    source_authority = _runtime_probabilistic_target_stage_source_authority(
        state=state, raw_attacker=raw_attacker, raw_target=raw_target,
        attacker=attacker, target=target,
    )
    capability = resolve_probabilistic_target_stage_effect_capability(
        move=move_metadata, source_authority=source_authority,
    )
    stage_authority = freeze_runtime_current_stage_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target,
    )
    target_substitute = _runtime_target_substitute_authority(
        substitute_state(state, target),
    )
    status, reason = capability.get("status", "rejected"), capability.get("reason")
    special_defense_stage = None
    if stage_authority.get("status") == "rejected":
        status, reason = "rejected", stage_authority.get("reason", "runtime_current_stage_authority_unavailable")
    elif not _known_current_stage(stage_authority, "special-defense"):
        if status == "resolved":
            status, reason = "incomplete", "target_special_defense_stage_unknown"
    else:
        special_defense_stage = deepcopy(stage_authority["stages"]["special-defense"])
    if target_substitute["status"] != "known" and status == "resolved":
        status, reason = "incomplete", "target_substitute_unknown"
    result = {
        "status": status,
        "schema_version": "runtime-d0-probabilistic-target-stage-effect-authority-v1",
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)),
        "target": deepcopy(dict(target)),
        "move": deepcopy(dict(move_metadata)),
        "source_authority": deepcopy(source_authority),
        "capability_resolution": deepcopy(capability),
        "current_stage_authority": deepcopy(stage_authority),
        "current_target_special_defense_stage": special_defense_stage,
        "target_substitute_authority": deepcopy(target_substitute),
        "provenance": "runtime_battle_state_v1_to_detached_probabilistic_target_stage_effect_authority_v1",
    }
    if status != "resolved" and isinstance(reason, str):
        result["reason"] = reason
    return result


def freeze_runtime_d0_thunderbolt_paralysis_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze exact D0 facts for the catalogued Thunderbolt paralysis rule.

    It deliberately does not decide damage-roll survival, apply paralysis, or
    branch outcomes; those belong to a later successful-hit-leaf consumer.
    """
    move_id = move_metadata.get("move_id") if isinstance(move_metadata, Mapping) else None
    active = strategy_d0.get("active_owners") if isinstance(strategy_d0, Mapping) else None
    if (
        not _valid_d0(strategy_d0) or not isinstance(move_id, str) or not move_id
        or not _owner(attacker) or not _owner(target) or attacker != strategy_d0["decision_owner"]
        or not isinstance(active, Mapping) or active.get(attacker["side"]) != dict(attacker)
        or active.get(target["side"]) != dict(target) or attacker["side"] == target["side"]
    ):
        return _result("rejected", "runtime_thunderbolt_paralysis_identity_or_move_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    raw_attacker = _roster(state, attacker["side"]).get(attacker["slot_index"])
    raw_target = _roster(state, target["side"]).get(target["slot_index"])
    if not isinstance(raw_attacker, Mapping) or not isinstance(raw_target, Mapping) or not _same_runtime_owner(raw_attacker, attacker) or not _same_runtime_owner(raw_target, target):
        return _result("rejected", "runtime_thunderbolt_paralysis_identity_mismatch")
    target_condition = freeze_runtime_current_condition_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, owner=target,
    )
    source_authority = _runtime_probabilistic_target_status_source_authority(
        state=state, raw_attacker=raw_attacker, raw_target=raw_target,
        attacker=attacker, target=target, target_condition=target_condition,
    )
    capability = resolve_probabilistic_target_status_effect_capability(
        move=move_metadata, source_authority=source_authority,
    )
    target_substitute = _runtime_target_substitute_authority(substitute_state(state, target))
    status, reason = capability.get("status", "rejected"), capability.get("reason")
    if target_condition.get("status") == "rejected":
        status, reason = "rejected", target_condition.get("reason", "runtime_current_condition_authority_unavailable")
    if target_substitute["status"] != "known" and status == "resolved":
        status, reason = "incomplete", "target_substitute_unknown"
    result = {
        "status": status,
        "schema_version": "runtime-d0-thunderbolt-paralysis-authority-v1",
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)),
        "move": deepcopy(dict(move_metadata)), "source_authority": deepcopy(source_authority),
        "capability_resolution": deepcopy(capability),
        "current_target_condition_authority": deepcopy(target_condition),
        "target_type_authority": deepcopy(source_authority["target_types"]),
        "target_substitute_authority": deepcopy(target_substitute),
        "provenance": "runtime_battle_state_v1_to_detached_thunderbolt_paralysis_authority_v1",
    }
    if status != "resolved" and isinstance(reason, str):
        result["reason"] = reason
    return result


def build_runtime_d0_strict_hit_probability_assessment(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], selected_move: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose strict detached authorities into one exact accuracy assessment.

    This is a D0 boundary only: all Gen 9 arithmetic remains in
    :mod:`advisor.strict_hit_probability`, and no reducer field is mutated.
    """
    active = strategy_d0.get("active_owners") if isinstance(strategy_d0, Mapping) else None
    if (
        not _valid_d0(strategy_d0) or not _owner(attacker) or not _owner(target)
        or attacker != strategy_d0["decision_owner"] or not isinstance(active, Mapping)
        or active.get(attacker["side"]) != dict(attacker) or active.get(target["side"]) != dict(target)
        or attacker["side"] == target["side"]
    ):
        return _result("rejected", "runtime_strict_hit_probability_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    if not isinstance(selected_move, Mapping):
        return _result("rejected", "invalid_hit_probability_move")
    if selected_move.get("always_hit") is True:
        result = assess_strict_deterministic_hit_probability(
            move=selected_move, strict_stage_authority=None, modifier_authority=None,
        )
        if result.get("status") == "resolved":
            result.update(
                session_id=strategy_d0["session_id"],
                source_runtime_fingerprint=strategy_d0["source_runtime_fingerprint"],
                source_branch_fingerprint=strategy_d0["strategy_preview_fingerprint"],
                decision_owner=deepcopy(dict(strategy_d0["decision_owner"])),
                attacker=deepcopy(dict(attacker)), target=deepcopy(dict(target)),
                provenance="runtime_d0_strict_hit_probability_v1",
            )
        return result
    move = _hit_modifier_move(selected_move)
    if move is None:
        return _result("rejected", "invalid_hit_probability_move")
    modifier = freeze_runtime_d0_hit_modifier_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        attacker=attacker, target=target, move_metadata=move,
    )
    result = assess_strict_deterministic_hit_probability(
        move=selected_move, strict_stage_authority=modifier.get("strict_stage_authority"),
        modifier_authority=modifier,
    )
    if result.get("status") in {"resolved", "incomplete", "unsupported"}:
        result["decision_owner"] = deepcopy(dict(strategy_d0["decision_owner"]))
        result["provenance"] = "runtime_d0_strict_hit_probability_v1"
    return result


def freeze_runtime_seismic_toss_predictive_input(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_id: str,
) -> dict[str, Any]:
    """Freeze the strict current input consumed by predictive Seismic Toss.

    This boundary deliberately reads only the reducer snapshot tied to D0.  The
    current runtime schema does not own attacker level or Substitute state, so
    those remain explicit incomplete authority rather than borrowing profile,
    UI, or historical observation data.
    """
    if not _valid_d0(strategy_d0) or not _owner(attacker) or not _owner(target):
        return _result("rejected", "invalid_strategy_d0_or_predictive_owner")
    if move_id != "seismic-toss":
        return _result("rejected", "unsupported_predictive_move")
    owner = strategy_d0["decision_owner"]
    active_owners = strategy_d0.get("active_owners")
    if (
        attacker != owner or not isinstance(active_owners, Mapping)
        or active_owners.get(attacker["side"]) != dict(attacker)
        or active_owners.get(target["side"]) != dict(target)
        or attacker["side"] == target["side"]
    ):
        return _result("rejected", "runtime_predictive_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    raw_target = _roster(state, target["side"]).get(target["slot_index"])
    preview_target = strategy_d0["strategy_state"].get("active", {}).get(target["side"])
    if not isinstance(raw_target, Mapping) or not _same_runtime_owner(raw_target, target) or not _exact_preview_hp(preview_target):
        return _incomplete_seismic_toss_input(strategy_d0, attacker, target, "target_hp_unknown", target_type=None)
    raw_attacker = _roster(state, attacker["side"]).get(attacker["slot_index"])
    target_type = _runtime_current_type(raw_target)
    level = _runtime_attacker_level(raw_attacker)
    substitute = substitute_state(strategy_d0["strategy_state"], target)
    missing = []
    if level is None:
        missing.append("attacker_level_runtime_untracked")
    if target_type is None:
        missing.append("target_type_unknown")
    if substitute.get("state") in {"unknown", "legacy_untracked"}:
        missing.append("substitute_state_unknown")
    if missing:
        return _incomplete_seismic_toss_input(
            strategy_d0, attacker, target, missing[0], target_type=target_type,
            missing_authority=missing, level=level, substitute=substitute,
        )
    predictive_input = {
        "schema_version": "current-predictive-fixed-damage-input-v1",
        "provenance": "trusted_current_predictive_fixed_damage_input_v1",
        "session_id": strategy_d0["session_id"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)),
        "target": deepcopy(dict(target)),
        "move_id": "seismic-toss",
        "attacker_level_authority": {"status": "known", "value": level, "provenance": "runtime_battle_state_v1"},
        "target_type_authority": {"status": "known", "value": deepcopy(target_type), "provenance": "runtime_battle_state_v1"},
    }
    return {
        "status": "resolved",
        "schema_version": "deterministic-runtime-seismic-toss-predictive-input-v1",
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": "seismic-toss",
        "predictive_input": predictive_input,
        "target_hp_authority": {"status": "known", "current_hp": preview_target["current_hp"], "max_hp": preview_target["max_hp"]},
        "target_type_authority": deepcopy(predictive_input["target_type_authority"]),
        "substitute_authority": {"status": "known", "state": substitute["state"], **({"substitute_hp": substitute["substitute_hp"]} if "substitute_hp" in substitute else {})},
        "provenance": "runtime_battle_state_v1_seismic_toss_predictive_input_v1",
    }


def freeze_runtime_water_gun_predictive_input(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_id: str,
    native_damage_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze only runtime-owned Water Gun authority for the native interval path.

    This is deliberately a producer boundary, not a second snapshot builder or
    damage calculator.  A supplied native context must have been frozen by
    ``build_runtime_d0_native_damage_context`` for this exact D0.
    """
    if not _valid_d0(strategy_d0) or not _owner(attacker) or not _owner(target):
        return _result("rejected", "invalid_strategy_d0_or_predictive_owner")
    if move_id != "water-gun":
        return _result("rejected", "unsupported_predictive_move")
    active = strategy_d0.get("active_owners")
    if (
        attacker != strategy_d0["decision_owner"] or not isinstance(active, Mapping)
        or active.get(attacker["side"]) != dict(attacker)
        or active.get(target["side"]) != dict(target) or attacker["side"] == target["side"]
    ):
        return _result("rejected", "runtime_predictive_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    raw_attacker = _roster(state, attacker["side"]).get(attacker["slot_index"])
    raw_target = _roster(state, target["side"]).get(target["slot_index"])
    if not isinstance(raw_attacker, Mapping) or not isinstance(raw_target, Mapping) or not _same_runtime_owner(raw_attacker, attacker) or not _same_runtime_owner(raw_target, target):
        return _result("rejected", "runtime_predictive_identity_mismatch")
    preview_target = strategy_d0["strategy_state"].get("active", {}).get(target["side"])
    substitute = substitute_state(strategy_d0["strategy_state"], target)
    field_state = state.get("field") if isinstance(state.get("field"), Mapping) else {}
    fields = {
        "attacker_level": _known_authority(_runtime_attacker_level(raw_attacker)),
        "attacker_final_special_attack": _runtime_final_stat_field(raw_attacker, "special-attack"),
        "target_final_special_defense": _runtime_final_stat_field(raw_target, "special-defense"),
        "attacker_current_type": _known_authority(_runtime_current_type(raw_attacker)),
        "target_current_type": _known_authority(_runtime_current_type(raw_target)),
        "attacker_special_attack_stage": _stage_authority(raw_attacker, "special-attack"),
        "target_special_defense_stage": _stage_authority(raw_target, "special-defense"),
        "target_hp": _known_authority(
            {"current_hp": preview_target["current_hp"], "max_hp": preview_target["max_hp"]}
            if _exact_preview_hp(preview_target) else None
        ),
        "attacker_item": _runtime_known_field(raw_attacker.get("known_item"), "runtime_item_unknown"),
        "target_item": _runtime_known_field(raw_target.get("known_item"), "runtime_item_unknown"),
        "attacker_ability": _runtime_known_field(raw_attacker.get("current_ability"), "runtime_ability_unknown"),
        "target_ability": _runtime_known_field(raw_target.get("current_ability"), "runtime_ability_unknown"),
        "weather": _runtime_known_field(field_state.get("weather"), "runtime_weather_unknown"),
        "terrain": _runtime_known_field(field_state.get("terrain"), "runtime_terrain_unknown"),
        "substitute": _substitute_authority(substitute),
    }
    missing = [name for name, authority in fields.items() if not isinstance(authority, Mapping) or authority.get("status") != "known"]
    context = _runtime_native_context_for_water_gun(
        native_damage_context, strategy_d0=strategy_d0, attacker=attacker, target=target,
    )
    if context.get("status") == "resolved":
        return {
            "status": "resolved", "schema_version": "deterministic-runtime-water-gun-predictive-input-v1",
            "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
            "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
            "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": "water-gun",
            "authority_fields": deepcopy(fields), "snapshot_damage_input": deepcopy(context["snapshot_damage_input"]),
            "stat_provenance": deepcopy(context["stat_provenance"]), "trusted_level": context["trusted_level"],
            "provenance": "runtime_battle_state_v1_water_gun_native_context_v1",
        }
    missing.extend(context.get("missing_authority", ["runtime_native_damage_context_unavailable"]))
    if native_damage_context is None:
        # Preserve the pre-context boundary's public reason for callers that
        # have not yet supplied the new canonical producer.
        missing.extend(["runtime_snapshot_damage_input_unavailable", "runtime_stat_provenance_unavailable"])
    return {
        "status": "incomplete", "schema_version": "deterministic-runtime-water-gun-predictive-input-v1",
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": "water-gun",
        "authority_fields": deepcopy(fields), "missing_authority": missing,
        "reason": missing[0] if missing else "runtime_native_damage_context_unavailable",
        "provenance": "runtime_battle_state_v1_water_gun_predictive_input_boundary_v1",
    }


def freeze_runtime_normal_formula_predictive_input(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
    native_damage_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Generic D0 producer for metadata-eligible, immediate normal-formula damage."""
    eligibility = normal_formula_eligibility(move_metadata)
    if eligibility.get("status") != "eligible":
        return _result("unsupported", eligibility.get("reason", "unsupported_predictive_move"))
    if not _valid_d0(strategy_d0) or not _owner(attacker) or not _owner(target):
        return _result("rejected", "invalid_strategy_d0_or_predictive_owner")
    active = strategy_d0.get("active_owners")
    if attacker != strategy_d0["decision_owner"] or not isinstance(active, Mapping) or active.get(attacker["side"]) != dict(attacker) or active.get(target["side"]) != dict(target) or attacker["side"] == target["side"]:
        return _result("rejected", "runtime_predictive_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current": return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    raw_attacker = _roster(state, attacker["side"]).get(attacker["slot_index"])
    raw_target = _roster(state, target["side"]).get(target["slot_index"])
    preview_attacker = strategy_d0["strategy_state"].get("active", {}).get(attacker["side"])
    item_authority = _native_item_authority(raw_attacker.get("known_item"), raw_attacker.get("known_item_provenance")) if isinstance(raw_attacker, Mapping) else {"available": False}
    attacker_ability = _runtime_known_string(raw_attacker.get("current_ability")) if isinstance(raw_attacker, Mapping) else None
    target_ability = _runtime_known_string(raw_target.get("current_ability")) if isinstance(raw_target, Mapping) else None
    post_hit_authority = {
        "attacker_hp": {"current_hp": preview_attacker.get("current_hp"), "max_hp": preview_attacker.get("max_hp")} if _exact_preview_hp(preview_attacker) else None,
        "attacker_item": item_authority.get("value"),
        "attacker_item_known": item_authority.get("available") is True,
        "attacker_ability": attacker_ability,
        "target_ability": target_ability,
    }
    context = _runtime_native_context_for_normal_formula(native_damage_context, strategy_d0=strategy_d0, attacker=attacker, target=target, move_id=eligibility["move_id"])
    base = {"schema_version": "deterministic-runtime-normal-formula-predictive-input-v1", "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])), "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": eligibility["move_id"], "move_metadata": deepcopy(dict(move_metadata)), "provenance": "runtime_battle_state_v1_normal_formula_native_context_v1"}
    if context.get("status") == "resolved":
        return {"status": "resolved", **base, "snapshot_damage_input": deepcopy(context["snapshot_damage_input"]), "stat_provenance": deepcopy(context["stat_provenance"]), "trusted_level": context["trusted_level"], "post_hit_authority": deepcopy(post_hit_authority), "stage_effect_authority": deepcopy(eligibility["stage_effect_authority"])}
    missing = list(context.get("missing_authority", [])) or [context.get("reason", "runtime_native_damage_context_incomplete")]
    return {"status": "incomplete", **base, "missing_authority": missing, "reason": missing[0]}


def freeze_runtime_final_combat_stat_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], owner: Mapping[str, Any], stat: str,
) -> dict[str, Any]:
    """Freeze one identity-bound, stage-unmodified final combat stat at D0."""
    if not _valid_d0(strategy_d0) or not _owner(owner) or stat not in {"attack", "defense", "special-attack", "special-defense", "speed"}:
        return _result("rejected", "invalid_runtime_final_combat_stat_request")
    if not isinstance(strategy_d0.get("active_owners"), Mapping) or strategy_d0["active_owners"].get(owner["side"]) != dict(owner):
        return _result("rejected", "runtime_final_combat_stat_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    pokemon = _roster(state, owner["side"]).get(owner["slot_index"])
    authority = _runtime_final_stat_field(pokemon, stat) if isinstance(pokemon, Mapping) and _same_runtime_owner(pokemon, owner) else _unavailable_authority("runtime_final_combat_stat_identity_unknown")
    result = {
        "status": "resolved" if authority.get("status") == "known" else "incomplete",
        "schema_version": "runtime-final-combat-stat-authority-v1",
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "owner": deepcopy(dict(owner)), "stat": stat,
        "final_stat_authority": deepcopy(authority),
        "stage_authority": _stage_authority(pokemon, stat) if isinstance(pokemon, Mapping) else _unavailable_authority("runtime_stat_stage_unknown"),
        "provenance": "runtime_battle_state_v1_final_combat_stat_authority_v1",
    }
    if result["status"] == "incomplete":
        result["reason"] = authority.get("reason", "runtime_final_combat_stat_untracked")
    return result


def build_runtime_d0_native_damage_context(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze native snapshot/provenance shapes from one runtime D0.

    The returned ``snapshot_damage_input`` and ``stat_provenance`` deliberately
    retain the native evaluator's existing shapes.  This adapter only maps
    reducer-owned facts and marks absent authority as unknown; it never derives
    stats, types, modifiers, or move metadata from UI state.
    """
    if not _valid_d0(strategy_d0) or not _owner(attacker) or not _owner(target) or not isinstance(move_metadata, Mapping):
        return _native_context_result("rejected", "invalid_runtime_native_damage_request")
    move = _native_move_metadata(move_metadata)
    active = strategy_d0.get("active_owners")
    if (
        move is None or attacker != strategy_d0["decision_owner"] or not isinstance(active, Mapping)
        or active.get(attacker["side"]) != dict(attacker) or active.get(target["side"]) != dict(target)
        or attacker["side"] == target["side"]
    ):
        return _native_context_result("rejected", "runtime_native_damage_identity_mismatch")
    freshness = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if freshness.get("status") != "current":
        return _native_context_result("rejected", freshness.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    raw_attacker = _roster(state, attacker["side"]).get(attacker["slot_index"])
    raw_target = _roster(state, target["side"]).get(target["slot_index"])
    if not isinstance(raw_attacker, Mapping) or not isinstance(raw_target, Mapping) or not _same_runtime_owner(raw_attacker, attacker) or not _same_runtime_owner(raw_target, target):
        return _native_context_result("rejected", "runtime_native_damage_identity_mismatch")
    attacker_adapter = native_damage_stage_authority(strategy_d0.get("current_stage_authority", {}).get(attacker["side"], {}))
    target_adapter = native_damage_stage_authority(strategy_d0.get("current_stage_authority", {}).get(target["side"], {}))
    attacker_stages = attacker_adapter.get("stages") if attacker_adapter.get("status") == "resolved" else None
    target_stages = target_adapter.get("stages") if target_adapter.get("status") == "resolved" else None
    preview = strategy_d0["strategy_state"].get("active", {})
    preview_attacker, preview_target = preview.get(attacker["side"]), preview.get(target["side"])
    attacker_side = _native_runtime_side(raw_attacker, preview_attacker, attacker, attacker_stages)
    target_side = _native_runtime_side(raw_target, preview_target, target, target_stages)
    modifier_authority = _runtime_direct_damage_modifier_authority(
        state=state, attacker=attacker, target=target,
        raw_attacker=raw_attacker, raw_target=raw_target,
    )
    current = {
        "direct_mechanics_context": {
            "generation": "gen9",
            "attacker": _native_direct_side(raw_attacker, preview_attacker, attacker_stages),
            "defender": _native_direct_side(raw_target, preview_target, target_stages),
            "field": _native_field_direct_context(state),
        },
        "current_type_context": {"current_types": _native_type_entries(raw_attacker, raw_target)},
        "stat_stage_context": {"current_stages": _native_stage_entries(attacker_stages, target_stages)},
        "field_state_context": {"current_field": _native_field_state(state)},
        "battle_format_context": _native_battle_format_context(state),
        "condition_context": {"current_conditions": _native_condition_entries(raw_attacker, raw_target)},
        "ability_context": {"current_abilities": _native_ability_entries(raw_attacker, raw_target)},
    }
    damage_input = {
        "attacker": {**deepcopy(dict(attacker)), "session_id": strategy_d0["session_id"]},
        "defender": {**deepcopy(dict(target)), "session_id": strategy_d0["session_id"]},
        "move": move,
        "battle_context": {"current_state": current, "observed_event_evidence": []},
        "calculation_limits": [
            "Runtime current authority is frozen at one strategy D0.",
            "Unknown runtime mechanics facts are not neutral defaults.",
        ],
    }
    provenance = {"attacker": attacker_side, "defender": target_side, "limits": [
        "Final combat stats are runtime observed, stage-unmodified values.",
        "Stat stages are supplied separately to the native evaluator.",
    ]}
    level = _runtime_attacker_level(raw_attacker)
    native = evaluate_direct_damage_mechanics(damage_input, stat_provenance=provenance, trusted_level=level)
    missing = list(native.get("missing_inputs", [])) if native.get("status") == "insufficient_context" else []
    result = {
        "status": "resolved" if native.get("status") == "known" else "incomplete",
        "schema_version": "runtime-d0-native-damage-context-v1",
        "session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)), "target": deepcopy(dict(target)), "move_id": move["move_id"],
        "snapshot_damage_input": deepcopy(damage_input), "stat_provenance": deepcopy(provenance),
        "trusted_level": level, "native_evaluation": deepcopy(native), "missing_authority": missing,
        "modifier_authority": deepcopy(modifier_authority),
        "provenance": "runtime_battle_state_v1_native_damage_context_v1",
    }
    if result["status"] != "resolved":
        result["reason"] = native.get("unsupported_reason") or (missing[0] if missing else "native_damage_context_incomplete")
    return result


def _native_context_result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": "runtime-d0-native-damage-context-v1", "reason": reason}


def _native_move_metadata(value: Mapping[str, Any]) -> dict[str, Any] | None:
    move_id, category, power, move_type = value.get("move_id"), value.get("category"), value.get("power"), value.get("type")
    if not isinstance(move_id, str) or not move_id or category not in {"physical", "special", "status"} or not isinstance(power, int) or isinstance(power, bool) or power < 1 or not isinstance(move_type, str) or not move_type:
        return None
    return deepcopy(dict(value))


def _hit_modifier_move(value: Any) -> dict[str, str] | None:
    if not isinstance(value, Mapping): return None
    move_id, category = value.get("move_id"), value.get("category")
    if not isinstance(move_id, str) or not move_id or category not in {"physical", "special", "status"}: return None
    return {"move_id": move_id, "category": category}


def _runtime_hustle_ability_authority(*, state: Mapping[str, Any], raw_attacker: Mapping[str, Any], attacker: Mapping[str, Any]) -> dict[str, Any]:
    """Project exact observed ability plus explicit applicability when relevant."""
    ability = _runtime_known_string(raw_attacker.get("current_ability"))
    if ability is None:
        # Reducer ability ``None`` has no absence provenance, so it is unknown.
        return {"status": "unknown"}
    result: dict[str, Any] = {"status": "known", "value": ability}
    if ability == "hustle":
        normalized = normalize_ability_applicability_context(
            state.get("ability_applicability_context"), session_id=attacker["session_id"],
            source=attacker, ability_id="hustle",
        )
        result["applicability"] = {"status": normalized["status"]}
    return result


def _runtime_probabilistic_self_stage_ability_authority(*, state: Mapping[str, Any], raw_attacker: Mapping[str, Any], attacker: Mapping[str, Any]) -> dict[str, Any]:
    """Project exact attacker ability and Sheer Force applicability only."""
    ability = _runtime_known_string(raw_attacker.get("current_ability"))
    if ability is None:
        return {"status": "unknown"}
    result: dict[str, Any] = {"status": "known", "value": ability}
    if ability == "sheer-force":
        applicability = normalize_ability_applicability_context(
            state.get("ability_applicability_context"), session_id=attacker["session_id"],
            source=attacker, ability_id="sheer-force",
        )
        result["applicability"] = {"status": applicability["status"]}
    return result


def _runtime_probabilistic_target_stage_source_authority(
    *, state: Mapping[str, Any], raw_attacker: Mapping[str, Any], raw_target: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any],
) -> dict[str, Any]:
    """Project precisely the three source slots owned by the target resolver."""
    attacker_ability = _runtime_probabilistic_self_stage_ability_authority(
        state=state, raw_attacker=raw_attacker, attacker=attacker,
    )
    target_ability = _runtime_known_string(raw_target.get("current_ability"))
    target_ability_authority: dict[str, Any] = (
        {"status": "known", "value": target_ability}
        if target_ability is not None else {"status": "unknown"}
    )
    if target_ability == "shield-dust":
        interaction = normalize_ability_interaction_context(
            state.get("ability_interaction_context"), session_id=target["session_id"],
            source=target, target=attacker,
        )
        target_ability_authority["interaction"] = {"status": interaction["status"]}
    item = _native_item_authority(
        raw_target.get("known_item"), raw_target.get("known_item_provenance"),
    )
    target_item_authority: dict[str, Any]
    if item["status"] == "known":
        target_item_authority = {"status": "known", "value": item["value"]}
    elif item["status"] == "known_absent":
        target_item_authority = {"status": "known_absent"}
    else:
        target_item_authority = {"status": "unknown"}
    return {
        "attacker_ability": attacker_ability,
        "target_ability": target_ability_authority,
        "target_item": target_item_authority,
    }


def _runtime_probabilistic_target_status_source_authority(
    *, state: Mapping[str, Any], raw_attacker: Mapping[str, Any], raw_target: Mapping[str, Any],
    attacker: Mapping[str, Any], target: Mapping[str, Any], target_condition: Mapping[str, Any],
) -> dict[str, Any]:
    """Project resolver-only status sources from exact current authority."""
    source = _runtime_probabilistic_target_stage_source_authority(
        state=state, raw_attacker=raw_attacker, raw_target=raw_target,
        attacker=attacker, target=target,
    )
    condition = target_condition.get("condition") if target_condition.get("status") == "resolved" else None
    if isinstance(condition, Mapping) and condition.get("status") == "known_none":
        source["target_condition"] = {"status": "known_none"}
    elif isinstance(condition, Mapping) and condition.get("status") == "known_present" and isinstance(condition.get("condition"), str):
        source["target_condition"] = {"status": "known_present", "condition": condition["condition"]}
    else:
        source["target_condition"] = {"status": "unknown"}
    current_types = _runtime_current_type(raw_target)
    source["target_types"] = (
        {"status": "known", "values": deepcopy(current_types)}
        if current_types is not None else {"status": "unknown"}
    )
    return source


def _runtime_target_substitute_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    """Expose tracked Substitute state without turning absent tracking into false."""
    state = value.get("state") if isinstance(value, Mapping) else None
    if state == "known_inactive":
        return {"status": "known", "state": state}
    if state == "known_active":
        hp = value.get("substitute_hp")
        if isinstance(hp, int) and not isinstance(hp, bool) and hp > 0:
            return {"status": "known", "state": state, "substitute_hp": hp}
    return {"status": "unknown"}


def _known_current_stage(authority: Mapping[str, Any], stat: str) -> bool:
    stages = authority.get("stages") if isinstance(authority, Mapping) else None
    value = stages.get(stat) if isinstance(stages, Mapping) else None
    return isinstance(value, Mapping) and value.get("status") == "known" and isinstance(value.get("value"), int) and not isinstance(value.get("value"), bool) and -6 <= value["value"] <= 6


def _runtime_critical_hit_sources(*, raw_attacker: Mapping[str, Any], raw_target: Mapping[str, Any]) -> dict[str, Any]:
    """Project only resolver slots; omitted optional slots remain unknown there."""
    return {
        "attacker_ability": _runtime_critical_ability(raw_attacker),
        "defender_ability": _runtime_critical_ability(raw_target),
        "attacker_item": _runtime_critical_item(raw_attacker),
        "target_condition": _runtime_critical_condition(raw_target),
        "attacker_types": _runtime_critical_types(raw_attacker),
    }


def _runtime_critical_ability(raw: Mapping[str, Any]) -> dict[str, Any]:
    value = _runtime_known_string(raw.get("current_ability"))
    return {"status": "known", "value": value} if value is not None else {"status": "unknown"}


def _runtime_critical_item(raw: Mapping[str, Any]) -> dict[str, Any]:
    item = _native_item_authority(raw.get("known_item"), raw.get("known_item_provenance"))
    return {"status": "known", "value": item["value"]} if item["status"] == "known" else {"status": item["status"]}


def _runtime_critical_condition(raw: Mapping[str, Any]) -> dict[str, Any]:
    value = _runtime_known_string(raw.get("condition"))
    if value is None:
        return {"status": "unknown"}
    return {"status": "known_absent"} if value == "none" else {"status": "known", "value": value}


def _runtime_critical_types(raw: Mapping[str, Any]) -> dict[str, Any]:
    value = _runtime_current_type(raw)
    return {"status": "known", "value": value} if value is not None else {"status": "unknown"}


def _native_runtime_side(raw: Mapping[str, Any], preview: Any, owner: Mapping[str, Any], stage_map: Mapping[str, int] | None = None) -> dict[str, Any]:
    final_values = {stat: _runtime_final_stat_field(raw, stat).get("value") for stat in _NATIVE_STAGE_KEYS}
    if _exact_preview_hp(preview):
        final_values["hp"] = preview["max_hp"]
    complete_stats = all(isinstance(final_values.get(key), int) and not isinstance(final_values[key], bool) and final_values[key] > 0 for key in _NATIVE_STAT_KEYS)
    current_type = _runtime_current_type(raw)
    item = _native_item_authority(raw.get("known_item"), raw.get("known_item_provenance"))
    return {
        "pokemon_identity": owner["pokemon_id"], "side": owner["side"], "slot_index": owner["slot_index"], "session_id": owner["session_id"],
        "types": _native_provenance_block(current_type, "runtime_current_type", "runtime_current", "current_type_unknown"),
        "type_authority": {"status": "known", "basis": "current_type_context", "reason": None} if current_type is not None else {"status": "unknown", "basis": "current_type_context", "reason": "current_type_unknown"},
        "base_stats": _native_provenance_block(None, "not_used_by_runtime_native_context", "unknown", "base_stats_not_runtime_authority"),
        "final_stats": _native_provenance_block(final_values if complete_stats else None, "runtime_final_combat_stat_authority_v1", "runtime_current", "final_stats_unavailable"),
        "stat_stages": _native_provenance_block(stage_map, "runtime_current_stat_stage", "runtime_current", "stat_stages_unavailable"),
        "known_ability": _native_provenance_block(_runtime_known_string(raw.get("current_ability")), "runtime_current_ability", "runtime_current", "ability_unknown"),
        "known_item": item,
    }


def _native_provenance_block(value: Any, source: str, trust: str, reason: str) -> dict[str, Any]:
    return {"available": value is not None, "value": deepcopy(value) if value is not None else None, "source": source if value is not None else "unknown", "trust": trust if value is not None else "unknown", "reason": None if value is not None else reason}


def _runtime_known_string(value: Any) -> str | None:
    return value if isinstance(value, str) and bool(value) and not is_unknown_battle_fact(value) else None


def _runtime_crit_volatiles_exact(raw: Any) -> list[str] | None:
    values = raw.get("current_crit_volatiles") if isinstance(raw, Mapping) else None
    provenance = raw.get("current_crit_volatiles_provenance") if isinstance(raw, Mapping) else None
    allowed = {"focus-energy", "lansat", "dragon-cheer"}
    if not isinstance(values, list) or len(values) != len(set(values)) or any(value not in allowed for value in values) or not isinstance(provenance, Mapping) or provenance.get("event_kind") != "current_crit_volatiles_observed" or provenance.get("trust") != "user_confirmed_observation":
        return None
    return values


def _runtime_side_conditions_exact(raw: Any) -> list[str] | None:
    values = raw.get("side_conditions") if isinstance(raw, Mapping) else None
    provenance = raw.get("side_conditions_provenance") if isinstance(raw, Mapping) else None
    if not isinstance(values, list) or not isinstance(provenance, Mapping) or provenance.get("trust") != "user_confirmed_observation" or provenance.get("event_kind") not in {"current_side_conditions_observed", "side_condition_started_observed", "side_condition_ended_observed"}:
        return None
    return values


def _native_item_authority(value: Any, provenance: Any = None) -> dict[str, Any]:
    if isinstance(value, str) and value and not is_unknown_battle_fact(value):
        return {"available": True, "status": "known", "value": value, "source": "runtime_current_item", "trust": "runtime_current", "reason": None, "profile_source": "runtime_battle_state_v1"}
    if value is None and isinstance(provenance, Mapping) and provenance.get("event_kind") in {"current_item_observed", "item_consumption_observed", "item_removed_observed"}:
        return {"available": True, "status": "known_absent", "value": None, "source": "runtime_current_item", "trust": "runtime_current", "reason": None, "profile_source": "runtime_battle_state_v1"}
    return {"available": False, "status": "unknown", "value": None, "source": "unknown", "trust": "unknown", "reason": "item_unknown", "profile_source": "runtime_battle_state_v1"}


def _native_stage_map(raw: Mapping[str, Any]) -> dict[str, int] | None:
    stages = raw.get("stat_stages")
    if not isinstance(stages, Mapping):
        return None
    result = {key: stages.get(key) for key in _NATIVE_STAGE_KEYS}
    return result if all(isinstance(value, int) and not isinstance(value, bool) and -6 <= value <= 6 for value in result.values()) else None


def _native_direct_side(raw: Mapping[str, Any], preview: Any, stage_map: Mapping[str, int] | None = None) -> dict[str, Any]:
    hp = preview if _exact_preview_hp(preview) else {}
    condition = _runtime_known_string(raw.get("condition"))
    ability = _runtime_known_string(raw.get("current_ability"))
    item_authority = _native_item_authority(raw.get("known_item"), raw.get("known_item_provenance"))
    item = item_authority.get("value")
    return {
        "ability": {"status": "known", "value": ability} if ability else {"status": "unknown"},
        "item": {"status": item_authority["status"], **({"value": item} if item_authority["status"] == "known" else {})},
        # This native legacy field remains a zero baseline only when the
        # separately-authoritative full stage map is exact; evaluator stage
        # application continues to happen only in its canonical stage path.
        "boosts": {key: 0 for key in _NATIVE_STAGE_KEYS} if stage_map is not None else {"status": "unknown"},
        "current_hp": hp.get("current_hp"), "max_hp": hp.get("max_hp"),
        "status": {"status": "known_absent"} if condition == "none" else ({"status": "known", "value": condition} if condition else {"status": "unknown"}),
    }


def _native_type_entries(attacker: Mapping[str, Any], target: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for side, raw in (("self", attacker), ("opponent", target)):
        current_type = _runtime_current_type(raw)
        rows.append({"side": side, "state": "known", "types": current_type, "status": "user_confirmed", "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current"} if current_type is not None else {"side": side, "state": "unknown", "status": "unknown", "source": "unknown", "authority_provenance": "unknown"})
    return rows


def _native_stage_entries(attacker: Mapping[str, int] | None, target: Mapping[str, int] | None) -> list[dict[str, Any]]:
    rows = []
    for side, stages in (("self", attacker), ("opponent", target)):
        if stages is not None:
            rows.extend({"side": side, "stat": stat, "stage": value, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage", "confidence": "known"} for stat, value in stages.items())
    return rows


def _native_condition_entries(attacker: Mapping[str, Any], target: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"side": side, "condition_type": _runtime_known_string(raw.get("condition")) or "unknown", "status": "user_confirmed" if _runtime_known_string(raw.get("condition")) else "unknown", "source": "user_confirmed_current_condition" if _runtime_known_string(raw.get("condition")) else "unknown"} for side, raw in (("self", attacker), ("opponent", target))]


def _native_ability_entries(attacker: Mapping[str, Any], target: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"side": side, "ability": _runtime_known_string(raw.get("current_ability")) or "unknown", "status": "user_confirmed" if _runtime_known_string(raw.get("current_ability")) else "unknown", "source": "user_confirmed_current_ability" if _runtime_known_string(raw.get("current_ability")) else "unknown"} for side, raw in (("self", attacker), ("opponent", target))]


def _native_field_direct_context(state: Mapping[str, Any]) -> dict[str, Any]:
    field = state.get("field") if isinstance(state.get("field"), Mapping) else {}
    weather, terrain = field.get("weather"), field.get("terrain")
    return {"weather": {"status": "known", "value": weather} if _runtime_weather_exact(field) else {"status": "unknown"}, "terrain": {"status": "known", "value": terrain} if _runtime_terrain_exact(field) else {"status": "unknown"}}


def _native_field_state(state: Mapping[str, Any]) -> dict[str, Any]:
    field = state.get("field") if isinstance(state.get("field"), Mapping) else {}
    weather, terrain = field.get("weather"), field.get("terrain")
    return {"weather": weather if _runtime_weather_exact(field) else "unknown", "terrain": terrain if _runtime_terrain_exact(field) else "unknown", "side_effects": _native_side_effects(state)}


def _native_battle_format_context(state: Mapping[str, Any]) -> dict[str, Any]:
    field = state.get("field") if isinstance(state.get("field"), Mapping) else {}
    value = field.get("battle_format")
    provenance = field.get("battle_format_provenance")
    exact = isinstance(value, str) and isinstance(provenance, Mapping) and provenance.get("trust") == "user_confirmed_observation" and provenance.get("event_kind") in {"session_battle_format_initialized", "current_battle_format_observed"}
    return {"current_battle_format": {"battle_format": value} if exact else {"battle_format": "unknown"}}


def _runtime_weather_exact(field: Mapping[str, Any]) -> bool:
    provenance = field.get("weather_provenance")
    return isinstance(field.get("weather"), str) and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_weather_observed" and provenance.get("trust") == "user_confirmed_observation"


def _runtime_terrain_exact(field: Mapping[str, Any]) -> bool:
    provenance = field.get("terrain_provenance")
    return isinstance(field.get("terrain"), str) and isinstance(provenance, Mapping) and provenance.get("event_kind") == "current_terrain_observed" and provenance.get("trust") == "user_confirmed_observation"


def _native_side_effects(state: Mapping[str, Any]) -> list[dict[str, str]] | str:
    rows: list[dict[str, str]] = []
    for side_name in ("self", "opponent"):
        side = state.get(f"{side_name}_side")
        conditions = side.get("side_conditions") if isinstance(side, Mapping) else None
        provenance = side.get("side_conditions_provenance") if isinstance(side, Mapping) else None
        if not isinstance(conditions, list) or not isinstance(provenance, Mapping) or provenance.get("trust") != "user_confirmed_observation" or provenance.get("event_kind") not in {"current_side_conditions_observed", "side_condition_started_observed", "side_condition_ended_observed"}:
            return "unknown"
        rows.extend({"side": side_name, "effect": effect} for effect in conditions)
    return rows


def _runtime_direct_damage_modifier_authority(*, state: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], raw_attacker: Mapping[str, Any], raw_target: Mapping[str, Any]) -> dict[str, Any]:
    """Reusable D0-bound authority inventory; values are consumed through native shapes."""
    field = state.get("field") if isinstance(state.get("field"), Mapping) else {}
    effects = _native_side_effects(state)
    def side_conditions(side: str) -> dict[str, Any]:
        value = state.get(f"{side}_side")
        conditions = value.get("side_conditions") if isinstance(value, Mapping) else None
        return {"status": "known", "value": deepcopy(conditions)} if isinstance(effects, list) and isinstance(conditions, list) else {"status": "unknown", "value": None}
    format_context = _native_battle_format_context(state)["current_battle_format"]
    return {"schema_version": "runtime-direct-damage-modifier-authority-v1", "attacker": {"owner": deepcopy(dict(attacker)), "item": _native_item_authority(raw_attacker.get("known_item"), raw_attacker.get("known_item_provenance")), "ability": _native_provenance_block(_runtime_known_string(raw_attacker.get("current_ability")), "runtime_current_ability", "runtime_current", "ability_unknown"), "side_conditions": side_conditions(attacker["side"])}, "defender": {"owner": deepcopy(dict(target)), "item": _native_item_authority(raw_target.get("known_item"), raw_target.get("known_item_provenance")), "ability": _native_provenance_block(_runtime_known_string(raw_target.get("current_ability")), "runtime_current_ability", "runtime_current", "ability_unknown"), "side_conditions": side_conditions(target["side"])}, "field": {"weather": {"status": "known", "value": field.get("weather")} if _runtime_weather_exact(field) else {"status": "unknown", "value": None}, "terrain": {"status": "known", "value": field.get("terrain")} if _runtime_terrain_exact(field) else {"status": "unknown", "value": None}, "battle_format": {"status": "known", "value": format_context["battle_format"]} if format_context["battle_format"] in {"singles", "doubles"} else {"status": "unknown", "value": None}}}


def _runtime_native_context_for_water_gun(value: Any, *, strategy_d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    return _runtime_native_context_for_normal_formula(value, strategy_d0=strategy_d0, attacker=attacker, target=target, move_id="water-gun")


def _runtime_native_context_for_normal_formula(value: Any, *, strategy_d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], move_id: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != "runtime-d0-native-damage-context-v1":
        return {"status": "incomplete", "missing_authority": ["runtime_native_damage_context_unavailable"]}
    expected = {"session_id": strategy_d0["session_id"], "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"], "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"], "decision_owner": strategy_d0["decision_owner"], "attacker": attacker, "target": target, "move_id": move_id}
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        return {"status": "incomplete", "missing_authority": ["runtime_native_damage_context_d0_mismatch"]}
    if value.get("status") != "resolved" or not isinstance(value.get("snapshot_damage_input"), Mapping) or not isinstance(value.get("stat_provenance"), Mapping) or not isinstance(value.get("trusted_level"), int):
        return {"status": "incomplete", "missing_authority": list(value.get("missing_authority", [])) or [value.get("reason", "runtime_native_damage_context_incomplete")]}
    return {"status": "resolved", "snapshot_damage_input": value["snapshot_damage_input"], "stat_provenance": value["stat_provenance"], "trusted_level": value["trusted_level"]}


def runtime_strategy_d0_freshness(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Check reducer-fingerprint freshness without inspecting UI state."""
    if not _valid_d0(strategy_d0):
        return _result("rejected", "invalid_strategy_d0")
    _state, session_id, fingerprint = _runtime_snapshot(runtime_snapshot)
    if session_id is None or fingerprint is None:
        return _result("rejected", "invalid_runtime_snapshot")
    if session_id != strategy_d0["session_id"]:
        return _result("stale", "runtime_session_mismatch")
    if fingerprint != strategy_d0["source_runtime_fingerprint"]:
        return _result("stale", "runtime_fingerprint_changed")
    return {"status": "current", "source_runtime_fingerprint": fingerprint}


def freeze_runtime_strategy_selection_authority(*, strategy_d0: Mapping[str, Any], selection_projection: Mapping[str, Any]) -> dict[str, Any]:
    """Join already-validated structured selectability to one exact runtime D0.

    The projection provides selection facts only.  This adapter intentionally
    drops any execution-shaped payload rather than promoting it across the
    selection boundary.
    """
    if not _valid_d0(strategy_d0) or not isinstance(selection_projection, Mapping):
        return _result("rejected", "invalid_strategy_d0_or_selection_projection")
    owner = strategy_d0["decision_owner"]
    expected = {
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "decision_owner": owner,
        "active_owner": owner,
    }
    if any(selection_projection.get(key) != value for key, value in expected.items()):
        return _result("rejected", "selection_projection_runtime_d0_mismatch")
    moves, switches = selection_projection.get("moves"), selection_projection.get("switches")
    if not _selection_entries(moves, "move_id") or not _selection_entries(switches, "pokemon_id"):
        return _result("rejected", "invalid_selection_projection_records")
    fingerprint = strategy_d0["strategy_preview_fingerprint"]
    metadata_authorities = selection_projection.get("move_metadata_authorities")
    if metadata_authorities is not None and not isinstance(metadata_authorities, Mapping):
        return _result("rejected", "invalid_selectable_move_metadata_authorities")
    frozen_moves = [
        {
            "owner": deepcopy(owner), "source_branch_fingerprint": fingerprint,
            "move_id": row["move_id"], "selection": row["selection"],
            **({"move_metadata_authority": deepcopy(metadata_authorities.get(row["move_id"]))}
               if isinstance(metadata_authorities, Mapping) and isinstance(metadata_authorities.get(row["move_id"]), Mapping) else {}),
        }
        for row in moves
    ]
    frozen_switches = [
        {"owner": deepcopy(owner), "source_branch_fingerprint": fingerprint, "pokemon_id": row["pokemon_id"], "selection": row["selection"]}
        for row in switches
    ]
    return freeze_current_action_authority(
        decision_state=strategy_d0["strategy_state"], decision_owner=owner,
        moves=frozen_moves, switches=frozen_switches,
    )


def resolve_runtime_d0_selectable_move_metadata_authority(
    *, strategy_d0: Mapping[str, Any], action: Mapping[str, Any],
) -> dict[str, Any]:
    """Return one candidate's D0-bound canonical metadata without a raw lookup.

    This is deliberately structural: predictive builders retain ownership of
    mechanics and consume only the immutable ``metadata`` payload after the
    candidate/action and D0 bindings have been validated here.
    """
    if not _valid_d0(strategy_d0) or not isinstance(action, Mapping):
        return _result("rejected", "invalid_strategy_d0_or_action")
    move = action.get("identity")
    authority = action.get("move_metadata_authority")
    if action.get("action_type") != "attack" or not isinstance(move, str) or not move or not isinstance(authority, Mapping):
        return _result("rejected", "selectable_move_metadata_authority_missing")
    expected = {
        "candidate_id": action.get("action_id"), "move_id": move,
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": strategy_d0["decision_owner"],
        "active_attacker": strategy_d0["decision_owner"],
    }
    if any(authority.get(key) != value for key, value in expected.items()):
        return _result("rejected", "selectable_move_metadata_authority_binding_mismatch")
    status = authority.get("status")
    if status not in {"resolved", "incomplete", "unsupported", "rejected"}:
        return _result("rejected", "invalid_selectable_move_metadata_authority_status")
    return deepcopy(dict(authority))


def freeze_runtime_incoming_authority_boundary(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], incoming_owner: Mapping[str, Any]) -> dict[str, Any]:
    """Compatibility boundary for the canonical runtime incoming producer."""
    return freeze_runtime_incoming_current_state_authority(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        incoming_owner=incoming_owner,
    )


def freeze_runtime_incoming_current_state_authority(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], incoming_owner: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze strict current incoming-switch authority from one runtime roster.

    The reducer snapshot is the only source.  Exact HP and fainted authority
    are required by the existing incoming-active materializer; other roster
    facts are preserved as explicit known/unknown metadata and never defaulted
    merely because a Pokemon is on the bench.
    """
    if not _valid_d0(strategy_d0) or not _owner(incoming_owner):
        return _result("rejected", "invalid_strategy_d0_or_incoming_owner")
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    owner = strategy_d0["decision_owner"]
    if incoming_owner.get("session_id") != owner["session_id"] or incoming_owner.get("side") != owner["side"] or incoming_owner == owner:
        return _result("rejected", "foreign_or_active_incoming_owner")
    roster = _roster(state, owner["side"])
    current = roster.get(incoming_owner.get("slot_index")) if isinstance(roster, Mapping) else None
    if not isinstance(current, Mapping) or current.get("pokemon_id") != incoming_owner.get("pokemon_id"):
        return _result("rejected", "incoming_owner_not_in_runtime_roster")
    if sum(
        isinstance(row, Mapping) and row.get("pokemon_id") == incoming_owner["pokemon_id"]
        for row in roster.values()
    ) != 1:
        return _result("rejected", "ambiguous_runtime_incoming_identity")
    hp, maximum, fainted = current.get("current_hp"), current.get("max_hp"), current.get("fainted")
    if not _exact_hp(hp, maximum, fainted):
        if is_unknown_battle_fact(hp) or is_unknown_battle_fact(maximum):
            return _incomplete_incoming(strategy_d0, incoming_owner, "incoming_hp_unknown")
        if is_unknown_battle_fact(fainted):
            return _incomplete_incoming(strategy_d0, incoming_owner, "incoming_fainted_unknown")
        return _incomplete_incoming(strategy_d0, incoming_owner, "incoming_state_incomplete")
    if fainted:
        return _incomplete_incoming(strategy_d0, incoming_owner, "incoming_fainted")
    fields = _runtime_incoming_fields(current)
    current_state = {
        "current_state_session_id": owner["session_id"],
        "current_hp_context": {"current_hp": [{
            "side": owner["side"], "current_hp": hp, "maximum_hp": maximum,
            "status": "runtime_current_authority", "source": "runtime_battle_state_v1",
        }]},
        "condition_context": {"current_conditions": [{
            "side": owner["side"], "condition_type": fields["condition"].get("value", "unknown"),
            "status": "runtime_current_authority" if fields["condition"]["status"] == "known" else "unknown",
            "source": "runtime_battle_state_v1",
        }]},
        "runtime_incoming_current_state_authority": {
            "schema_version": "runtime-incoming-current-state-fields-v1",
            "owner": deepcopy(dict(incoming_owner)),
            "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
            "strategy_preview_fingerprint": strategy_d0["strategy_preview_fingerprint"],
            "fields": deepcopy(fields),
            "unknown_first": True,
        },
    }
    return {
        "status": "resolved",
        "schema_version": "identity-bound-incoming-current-state-v1",
        "session_id": owner["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(owner),
        "outgoing_owner": deepcopy(owner),
        "incoming_owner": deepcopy(dict(incoming_owner)),
        "owner": deepcopy(dict(incoming_owner)),
        "hp_authority": {"status": "known", "current_hp": hp, "maximum_hp": maximum, "provenance": "runtime_battle_state_v1"},
        "fainted_authority": {"status": "known", "value": False, "provenance": "runtime_battle_state_v1"},
        "current_state": current_state,
        "incoming_condition_authority": deepcopy(fields["condition"]),
        "incoming_item_authority": deepcopy(fields["item"]),
        "incoming_ability_authority": deepcopy(fields["ability"]),
        "incoming_type_authority": deepcopy(fields["type"]),
        "incoming_stage_authority": deepcopy(fields["stages"]),
        "incoming_substitute_authority": {"status": "unknown", "reason": "runtime_substitute_untracked"},
        "incoming_persistent_effect_authority": {"status": "unknown", "reason": "runtime_persistent_effects_untracked"},
        "execution_readiness": "execution_ready",
        "provenance": "identity_bound_incoming_current_state_v1",
    }


def resolve_runtime_incoming_owner(
    *, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], pokemon_id: str,
) -> dict[str, Any]:
    """Resolve one unique bench identity from the canonical runtime roster."""
    if not _valid_d0(strategy_d0) or not isinstance(pokemon_id, str) or not pokemon_id:
        return _result("rejected", "invalid_strategy_d0_or_incoming_identity")
    fresh = runtime_strategy_d0_freshness(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot)
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"))
    state, _session, _fingerprint = _runtime_snapshot(runtime_snapshot)
    owner = strategy_d0["decision_owner"]
    roster = _roster(state, owner["side"])
    matches = [
        {"session_id": owner["session_id"], "side": owner["side"], "slot_index": slot, "pokemon_id": pokemon_id}
        for slot, row in roster.items()
        if isinstance(slot, int) and not isinstance(slot, bool) and isinstance(row, Mapping) and row.get("pokemon_id") == pokemon_id
    ]
    if len(matches) != 1 or matches[0] == owner:
        return _result("rejected", "foreign_or_ambiguous_runtime_incoming_identity")
    return {"status": "resolved", "incoming_owner": matches[0]}


def _runtime_snapshot(value: Any) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if not isinstance(value, Mapping) or value.get("status") != "runtime_snapshot_ready":
        return None, None, None
    state = value.get("state")
    session_id = value.get("session_id")
    fingerprint = value.get("state_fingerprint")
    if (
        not isinstance(state, Mapping) or not isinstance(session_id, str) or not session_id
        or state.get("state_version") != STATE_MODEL_VERSION or state.get("session_id") != session_id
        or not validate_battle_state_unknown_markers(dict(state))
        or not isinstance(fingerprint, str) or fingerprint != state_fingerprint(dict(state))
    ):
        return None, None, None
    return deepcopy(dict(state)), session_id, fingerprint


def _active_owners(state: Mapping[str, Any], session_id: str) -> dict[str, dict[str, Any]] | None:
    owners: dict[str, dict[str, Any]] = {}
    for side, side_key in (("self", "self_side"), ("opponent", "opponent_side")):
        container = state.get(side_key)
        roster = container.get("pokemon") if isinstance(container, Mapping) else None
        slot = container.get("active_slot_index") if isinstance(container, Mapping) else None
        active = roster.get(slot) if isinstance(roster, Mapping) else None
        if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(active, Mapping) or not isinstance(active.get("pokemon_id"), str) or not active["pokemon_id"]:
            return None
        owners[side] = {"session_id": session_id, "side": side, "slot_index": slot, "pokemon_id": active["pokemon_id"]}
    return owners


def _preview_active(state: Mapping[str, Any], side: str, owner: Mapping[str, Any]) -> dict[str, Any]:
    raw = _roster(state, side).get(owner["slot_index"])
    result = deepcopy(dict(owner))
    if not isinstance(raw, Mapping):
        return result
    hp, maximum, fainted = raw.get("current_hp"), raw.get("max_hp"), raw.get("fainted")
    if _exact_hp(hp, maximum, fainted):
        result.update(current_hp=hp, max_hp=maximum, fainted=fainted)
    level = _runtime_attacker_level(raw)
    if level is not None:
        result["current_level"] = level
    if isinstance(raw.get("current_final_stats"), Mapping) and raw["current_final_stats"]:
        result["current_final_stats"] = deepcopy(dict(raw["current_final_stats"]))
    return result


def _runtime_authority_summary(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "runtime-strategy-current-authority-summary-v1",
        "active": {
            side: _fact_summary(_roster(state, side).get(_side_active_slot(state, side)))
            for side in ("self", "opponent")
        },
        "field": _fact_summary(state.get("field")),
        "unknown_first": True,
    }


def _fact_summary(value: Any) -> Any:
    if is_unknown_battle_fact(value):
        return {"status": "unknown"}
    if isinstance(value, Mapping):
        return {
            key: _fact_summary(item)
            for key, item in value.items()
            if key in {"current_level", "current_final_stats", "current_hp", "max_hp", "fainted", "condition", "known_item", "current_type", "current_ability", "stat_stages", "weather", "terrain", "battle_format", "side_conditions"}
        }
    return deepcopy(value)


def _side_active_slot(state: Mapping[str, Any], side: str) -> Any:
    container = state.get(f"{side}_side")
    return container.get("active_slot_index") if isinstance(container, Mapping) else None


def _roster(state: Mapping[str, Any], side: str) -> Mapping[str, Any]:
    container = state.get(f"{side}_side")
    roster = container.get("pokemon") if isinstance(container, Mapping) else None
    return roster if isinstance(roster, Mapping) else {}


def _exact_hp(hp: Any, maximum: Any, fainted: Any) -> bool:
    return (
        isinstance(hp, int) and not isinstance(hp, bool)
        and isinstance(maximum, int) and not isinstance(maximum, bool)
        and maximum > 0 and 0 <= hp <= maximum and isinstance(fainted, bool)
        and fainted is (hp == 0)
    )


def _runtime_incoming_fields(pokemon: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Copy only runtime-owned incoming fields; absent/untracked stays unknown."""
    return {
        "condition": _known_runtime_field(pokemon.get("condition")),
        "item": _known_runtime_field(pokemon.get("known_item")),
        "ability": _known_runtime_field(pokemon.get("current_ability")),
        "type": _known_runtime_field(pokemon.get("current_type")),
        # The reducer only owns stages when a current stage record exists.  A
        # missing record is deliberately not interpreted as a zero-stage bench.
        "stages": _known_runtime_field(pokemon.get("stat_stages")),
    }


def _known_runtime_field(value: Any) -> dict[str, Any]:
    if value is None or is_unknown_battle_fact(value):
        return {"status": "unknown"}
    return {"status": "known", "value": deepcopy(value), "provenance": "runtime_battle_state_v1"}


def _incomplete_incoming(strategy_d0: Mapping[str, Any], incoming_owner: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "status": "incomplete",
        "schema_version": "deterministic-runtime-incoming-authority-boundary-v1",
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "outgoing_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "incoming_owner": deepcopy(dict(incoming_owner)),
        "execution_readiness": "execution_incomplete",
        "reason": reason,
        "provenance": "runtime_roster_identity_boundary_v1",
    }


def _incomplete_seismic_toss_input(
    strategy_d0: Mapping[str, Any], attacker: Mapping[str, Any], target: Mapping[str, Any], reason: str,
    *, target_type: list[str] | None, missing_authority: Sequence[str] | None = None,
    level: int | None = None, substitute: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe known runtime facts without fabricating an invalid input schema."""
    preview_target = strategy_d0["strategy_state"]["active"][target["side"]]
    hp = (
        {"status": "known", "current_hp": preview_target["current_hp"], "max_hp": preview_target["max_hp"]}
        if _exact_preview_hp(preview_target) else {"status": "unknown"}
    )
    return {
        "status": "incomplete",
        "schema_version": "deterministic-runtime-seismic-toss-predictive-input-v1",
        "session_id": strategy_d0["session_id"],
        "source_runtime_fingerprint": strategy_d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": strategy_d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(strategy_d0["decision_owner"])),
        "attacker": deepcopy(dict(attacker)),
        "target": deepcopy(dict(target)),
        "move_id": "seismic-toss",
        "attacker_level_authority": (
            {"status": "known", "value": level, "provenance": "runtime_battle_state_v1"}
            if level is not None else {"status": "unknown", "reason": "attacker_level_runtime_untracked"}
        ),
        "target_hp_authority": hp,
        "target_type_authority": (
            {"status": "known", "value": deepcopy(target_type), "provenance": "runtime_battle_state_v1"}
            if target_type is not None else {"status": "unknown", "reason": "target_type_unknown"}
        ),
        "substitute_authority": (
            {"status": "known", "state": substitute["state"], **({"substitute_hp": substitute["substitute_hp"]} if "substitute_hp" in substitute else {})}
            if isinstance(substitute, Mapping) and substitute.get("state") not in {"unknown", "legacy_untracked"}
            else {"status": "unknown", "reason": "runtime_substitute_untracked"}
        ),
        "missing_authority": list(missing_authority or [reason]),
        "reason": reason,
        "provenance": "runtime_battle_state_v1_seismic_toss_predictive_input_boundary_v1",
    }


def _same_runtime_owner(value: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    return value.get("pokemon_id") == owner["pokemon_id"]


def _exact_preview_hp(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("current_hp"), int) and not isinstance(value.get("current_hp"), bool)
        and isinstance(value.get("max_hp"), int) and not isinstance(value.get("max_hp"), bool)
        and value["max_hp"] > 0 and 0 <= value["current_hp"] <= value["max_hp"]
        and value.get("fainted") is (value["current_hp"] == 0)
    )


def _runtime_current_type(value: Mapping[str, Any]) -> list[str] | None:
    current_type = value.get("current_type")
    if (
        isinstance(current_type, list) and bool(current_type)
        and all(isinstance(item, str) and bool(item) for item in current_type)
    ):
        return deepcopy(current_type)
    return None


def _runtime_attacker_level(value: Any) -> int | None:
    """Read a reducer-owned level only when the runtime schema provides one."""
    level = value.get("current_level") if isinstance(value, Mapping) else None
    return level if isinstance(level, int) and not isinstance(level, bool) and 1 <= level <= 100 else None


def _runtime_final_stat_field(pokemon: Any, stat: str) -> dict[str, Any]:
    stats = pokemon.get("current_final_stats") if isinstance(pokemon, Mapping) else None
    entry = stats.get(stat) if isinstance(stats, Mapping) else None
    if not isinstance(entry, Mapping) or not isinstance(entry.get("value"), int) or isinstance(entry.get("value"), bool) or entry["value"] < 1 or not isinstance(entry.get("provenance"), Mapping):
        return _unavailable_authority(f"runtime_final_{stat.replace('-', '_')}_untracked")
    return {"status": "known", "value": entry["value"], "provenance": deepcopy(dict(entry["provenance"]))}


def _known_authority(value: Any) -> dict[str, Any]:
    return (
        {"status": "known", "value": deepcopy(value), "provenance": "runtime_battle_state_v1"}
        if value is not None else {"status": "unknown"}
    )


def _unavailable_authority(reason: str) -> dict[str, Any]:
    return {"status": "unknown", "reason": reason}


def _runtime_known_field(value: Any, reason: str) -> dict[str, Any]:
    if value is None or is_unknown_battle_fact(value):
        return _unavailable_authority(reason)
    return _known_authority(value)


def _stage_authority(pokemon: Mapping[str, Any], stat: str) -> dict[str, Any]:
    stages = pokemon.get("stat_stages")
    value = stages.get(stat) if isinstance(stages, Mapping) else None
    return _known_authority(value) if isinstance(value, int) and not isinstance(value, bool) and -6 <= value <= 6 else _unavailable_authority("runtime_stat_stage_unknown")


def _substitute_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("state") in {"known_inactive", "known_active"}:
        result = {"status": "known", "state": value["state"], "provenance": "runtime_battle_state_v1"}
        if value.get("state") == "known_active":
            result["substitute_hp"] = value["substitute_hp"]
        return result
    return _unavailable_authority("runtime_substitute_unknown")


def _selection_entries(entries: Any, identity_key: str) -> bool:
    return (
        isinstance(entries, Sequence) and not isinstance(entries, (str, bytes))
        and all(isinstance(row, Mapping) and isinstance(row.get(identity_key), str) and bool(row[identity_key]) and row.get("selection") in {"selectable", "not_selectable", "selection_unknown"} for row in entries)
    )


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int) and not isinstance(value.get("slot_index"), bool) and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])
    )


def _valid_d0(value: Any) -> bool:
    if not isinstance(value, Mapping) or value.get("status") != "resolved" or value.get("schema_version") != SCHEMA:
        return False
    state = value.get("strategy_state")
    owner = value.get("decision_owner")
    return (
        _owner(owner) and value.get("session_id") == owner["session_id"]
        and isinstance(value.get("source_runtime_fingerprint"), str)
        and isinstance(value.get("strategy_preview_fingerprint"), str)
        and isinstance(state, Mapping) and state.get("schema_version") == PREVIEW_SCHEMA
        and fingerprint_transition_preview_state(state) == value["strategy_preview_fingerprint"]
    )


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
