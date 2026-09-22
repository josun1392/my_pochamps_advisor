"""Strict one-action detached execution boundary for gate consumers.

This module deliberately owns neither action opportunity nor action order.  It
adapts an already selected action to its existing family materializer and
returns branch-local post-action state to a later consumer.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0, runtime_strategy_d0_freshness
from llm.advisor_detached_predictive_intermediate_state import materialize_detached_predictive_intermediate_state
from llm.advisor_detached_direct_heal_materializer import materialize_detached_direct_heal
from llm.advisor_detached_atomic_item_swap_status_materializer import materialize_detached_atomic_item_swap_status
from llm.advisor_detached_pure_status_action_materializer import materialize_detached_pure_status_action
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_detached_predictive_intermediate_state import freeze_detached_actor_neutral_root_predictive_authority
from llm.advisor_runtime_d0_endure_turn_survival_authority import materialize_detached_endure_turn_context
from llm.advisor_champions_sleep_application import materialize_champions_rest, validate_champions_rest
from llm.advisor_detached_standard_charge_start import (
    materialize_detached_standard_charge_start,
)
from llm.advisor_runtime_d0_standard_charge_power_herb_skip_execution import (
    freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority,
    execute_runtime_d0_standard_charge_power_herb_skip,
)
from llm.advisor_geomancy_charge_status_terminal_execution import (
    freeze_runtime_d0_geomancy_power_herb_skip_execution_authority,
    execute_runtime_d0_geomancy_power_herb_skip,
)
from llm.advisor_runtime_d0_solar_weather_skip_execution import (
    freeze_runtime_d0_solar_weather_skip_execution_authority,
    execute_runtime_d0_solar_weather_skip,
)

SCHEMA_VERSION = "detached-selected-action-execution-result-v1"
_GRAPH_MOVES = frozenset({"bullet-seed", "rock-blast", "population-bomb", "triple-axel", "triple-kick"})
_STANDARD_CHARGE_MOVES = frozenset({"sky-attack", "razor-wind", "freeze-shock", "ice-burn", "solar-beam", "solar-blade", "meteor-beam", "skull-bash", "fly", "dig", "dive", "bounce", "phantom-force", "shadow-force", "geomancy"})


def materialize_detached_selected_action_execution_result(*, strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], move_metadata: Mapping[str, Any], family_authorities: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Execute exactly one already-permitted action without pair/order mass.

    ``family_authorities`` is deliberately sparse.  Existing family owners
    retain authority for special mechanics; an absent required authority is
    incomplete rather than an ordinary-attack fallback.
    """
    base = _base(strategy_d0, runtime_snapshot, action, actor, target, move_metadata)
    if base is None: return _result("rejected", "selected_action_execution_binding_invalid", {})
    metadata = move_metadata
    move_id = metadata["move_id"]
    authorities = family_authorities if isinstance(family_authorities, Mapping) else {}
    if move_id in _STANDARD_CHARGE_MOVES:
        readiness = authorities.get("standard_charge_start_readiness_authority")
        if isinstance(readiness, Mapping) and readiness.get("outcome") == "weather_charge_skip_ready":
            return _standard_charge_weather_skip(
                base, strategy_d0, runtime_snapshot, action, actor, target,
                move_metadata, readiness,
            )
        if isinstance(readiness, Mapping) and readiness.get("outcome") == "power_herb_charge_skip_ready":
            return _standard_charge_power_herb_skip(
                base, strategy_d0, runtime_snapshot, action, actor, target,
                move_metadata, readiness,
            )
        return _standard_charge_start(
            base, strategy_d0, runtime_snapshot, action, actor, target,
            readiness,
        )
    if move_id in _GRAPH_MOVES:
        return _graph(base, strategy_d0, runtime_snapshot, action, actor, target, metadata, authorities)
    if move_id in {"recover", "slack-off", "soft-boiled"}:
        return _direct_heal(base, runtime_snapshot, authorities.get("direct_heal_execution_authority"))
    if move_id == "rest":
        return _rest(base, strategy_d0, runtime_snapshot, action)
    if move_id in {"trick", "switcheroo"}:
        return _atomic_item_swap(base, strategy_d0, authorities.get("atomic_item_swap_execution_authority"))
    if move_id in {"taunt", "encore", "disable"}:
        return _status_special(base, strategy_d0, authorities.get("status_special_application_authority"))
    if move_id == "endure":
        return _endure(base, runtime_snapshot, authorities.get("endure_turn_survival_authority"))
    if move_id in {"protect", "detect", "quick-guard", "mat-block", "silk-trap", "kings-shield", "obstruct", "spiky-shield", "baneful-bunker", "burning-bulwark"}:
        return _protection(base, strategy_d0, runtime_snapshot, move_metadata, authorities.get("protection_execution_result"))
    if move_id in {"u-turn", "volt-switch", "flip-turn"}:
        return _pivot(base, strategy_d0, runtime_snapshot, action, actor, target, metadata, authorities)
    if metadata.get("category") not in {"physical", "special"}: return _result("unsupported", "selected_action_family_not_materialized", base)
    # Ordinary attack remains owned by the existing predictive attack ledger.
    from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger
    ledger = _attack_ledger(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
        actor=actor, target=target,
        metadata_authority={"status":"resolved", "metadata":deepcopy(dict(metadata))},
        action=action, endure_turn_survival_authority=authorities.get("endure_turn_context"),
    )
    if ledger.get("status") != "evaluable": return _result(ledger.get("status", "incomplete"), ledger.get("reason", "ordinary_selected_action_unavailable"), base)
    paths=[]
    for leaf in ledger.get("terminal_leaves", ()):
        state = materialize_detached_predictive_intermediate_state(strategy_d0=strategy_d0, terminal_leaf=leaf)
        if state.get("status") != "resolved": return _result(state.get("status", "incomplete"), state.get("reason", "ordinary_post_action_state_unavailable"), base)
        paths.append({"probability":deepcopy(leaf["probability"]), "action_leaf":deepcopy(leaf), "post_action_state":deepcopy(state)})
    return {"status":"resolved", "schema_version":SCHEMA_VERSION, **base, "execution_family":"ordinary_attack", "probability_owner":"selected_action_only", "paths":tuple(paths), "provenance":"selected_action_to_existing_predictive_attack_ledger_v1"}


def _standard_charge_weather_skip(
    base: Mapping[str, Any],
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    move_metadata: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    execution = freeze_runtime_d0_solar_weather_skip_execution_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata=move_metadata,
        readiness_authority=readiness,
    )
    if execution.get("status") != "resolved":
        return _result(execution.get("status", "incomplete"), execution.get("reason", "solar_weather_skip_execution_authority_unavailable"), base)
    kernel = execute_runtime_d0_solar_weather_skip(execution_authority=execution)
    if kernel.get("status") != "resolved":
        return _result(kernel.get("status", "incomplete"), kernel.get("reason", "solar_weather_terminal_execution_unavailable"), base)
    if kernel.get("terminal_probability_mass") != {"numerator": 1, "denominator": 1}:
        return _result("rejected", "solar_weather_terminal_probability_mass_invalid", base)
    leaves = kernel.get("terminal_leaves")
    if not isinstance(leaves, tuple) or not leaves:
        return _result("rejected", "solar_weather_terminal_leaves_missing", base)
    actor_item = execution["terminal_mechanics_authority"]["actor_participant_mechanics_authority"].get("item")
    retained = _solar_weather_retained_item(actor_item, execution)
    if retained is None:
        return _result("incomplete", "solar_weather_retained_item_authority_unavailable", base)
    paths = []
    for leaf in leaves:
        if not isinstance(leaf, Mapping):
            return _result("rejected", "solar_weather_terminal_leaf_invalid", base)
        leaf = deepcopy(dict(leaf))
        consequences = leaf.setdefault("consequences", {})
        consequences["solar_weather_skip_item_retention"] = deepcopy(dict(retained))
        state = materialize_detached_predictive_intermediate_state(strategy_d0=strategy_d0, terminal_leaf=leaf)
        if state.get("status") != "resolved":
            return _result(state.get("status", "incomplete"), state.get("reason", "solar_weather_post_action_state_unavailable"), base)
        paths.append({
            "probability": deepcopy(leaf["probability"]),
            "action_leaf": deepcopy(dict(leaf)),
            "post_action_state": state,
            "solar_weather_skip_execution_authority": deepcopy(dict(execution)),
            "pending_action_executed": False,
        })
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "execution_family": "standard_charge_weather_skip",
        "probability_owner": "selected_action_only",
        "paths": tuple(paths),
        "terminal_probability_mass": deepcopy(kernel["terminal_probability_mass"]),
        "shared_terminal_execution": deepcopy(dict(kernel)),
        "provenance": "selected_action_to_authenticated_solar_weather_skip_terminal_v1",
    }


def _solar_weather_retained_item(item: Any, execution: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(item, Mapping):
        return None
    status = item.get("status")
    if status == "known" and isinstance(item.get("value"), str) and item["value"]:
        item_after = {"status": "known", "value": item["value"]}
    elif status == "known_absent":
        item_after = {"status": "known_absent", "value": None}
    else:
        return None
    return {
        "status": "resolved",
        "schema_version": "solar-weather-skip-item-retention-v1",
        "actor": deepcopy(dict(execution["actor"])),
        "action_id": execution["action_id"],
        "move_id": execution["move_id"],
        "item_after": item_after,
        "source_execution_authority": deepcopy(dict(execution)),
        "provenance": "authenticated_solar_weather_skip_item_retention_v1",
    }


def _standard_charge_power_herb_skip(
    base: Mapping[str, Any],
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    move_metadata: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    if move_metadata.get("move_id") == "geomancy":
        execution = freeze_runtime_d0_geomancy_power_herb_skip_execution_authority(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            action=action,
            actor=actor,
            target=target,
            move_metadata=move_metadata,
            readiness_authority=readiness,
        )
        if execution.get("status") != "resolved":
            return _result(execution.get("status", "incomplete"), execution.get("reason", "geomancy_power_herb_skip_execution_authority_unavailable"), base)
        kernel = execute_runtime_d0_geomancy_power_herb_skip(execution)
        if kernel.get("status") != "resolved":
            return _result(kernel.get("status", "incomplete"), kernel.get("reason", "geomancy_power_herb_status_terminal_unavailable"), base)
        leaves = kernel.get("terminal_leaves")
        if kernel.get("terminal_probability_mass") != {"numerator": 1, "denominator": 1} or not isinstance(leaves, tuple) or not leaves:
            return _result("rejected", "geomancy_power_herb_terminal_ledger_invalid", base)
        paths = []
        for leaf in leaves:
            state = materialize_detached_predictive_intermediate_state(
                strategy_d0=strategy_d0,
                terminal_leaf=leaf,
            )
            if state.get("status") != "resolved":
                return _result(state.get("status", "incomplete"), state.get("reason", "geomancy_power_herb_post_action_state_unavailable"), base)
            paths.append({
                "probability": deepcopy(leaf["probability"]),
                "action_leaf": deepcopy(dict(leaf)),
                "post_action_state": state,
                "geomancy_power_herb_skip_execution_authority": deepcopy(dict(execution)),
                "pending_action_executed": False,
            })
        return {
            "status": "resolved",
            "schema_version": SCHEMA_VERSION,
            **deepcopy(dict(base)),
            "execution_family": "standard_charge_power_herb_skip",
            "probability_owner": "selected_action_only",
            "paths": tuple(paths),
            "terminal_probability_mass": deepcopy(kernel["terminal_probability_mass"]),
            "shared_terminal_execution": deepcopy(dict(kernel)),
            "provenance": "selected_action_to_authenticated_geomancy_power_herb_status_terminal_v1",
        }
    execution = freeze_runtime_d0_standard_charge_power_herb_skip_execution_authority(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        action=action,
        actor=actor,
        target=target,
        move_metadata=move_metadata,
        readiness_authority=readiness,
    )
    if execution.get("status") != "resolved":
        return _result(execution.get("status", "incomplete"), execution.get("reason", "power_herb_skip_execution_authority_unavailable"), base)
    kernel = execute_runtime_d0_standard_charge_power_herb_skip(execution_authority=execution)
    if kernel.get("status") != "resolved":
        return _result(kernel.get("status", "incomplete"), kernel.get("reason", "power_herb_terminal_execution_unavailable"), base)
    if kernel.get("terminal_probability_mass") != {"numerator": 1, "denominator": 1}:
        return _result("rejected", "power_herb_terminal_probability_mass_invalid", base)
    leaves = kernel.get("terminal_leaves")
    if not isinstance(leaves, tuple) or not leaves:
        return _result("rejected", "power_herb_terminal_leaves_missing", base)
    paths = []
    for leaf in leaves:
        if not isinstance(leaf, Mapping):
            return _result("rejected", "power_herb_terminal_leaf_invalid", base)
        state = materialize_detached_predictive_intermediate_state(
            strategy_d0=strategy_d0,
            terminal_leaf=leaf,
        )
        if state.get("status") != "resolved":
            return _result(state.get("status", "incomplete"), state.get("reason", "power_herb_post_action_state_unavailable"), base)
        paths.append({
            "probability": deepcopy(leaf["probability"]),
            "action_leaf": deepcopy(dict(leaf)),
            "post_action_state": state,
            "power_herb_skip_execution_authority": deepcopy(dict(execution)),
            "pending_action_executed": False,
        })
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "execution_family": "standard_charge_power_herb_skip",
        "probability_owner": "selected_action_only",
        "paths": tuple(paths),
        "terminal_probability_mass": deepcopy(kernel["terminal_probability_mass"]),
        "shared_terminal_execution": deepcopy(dict(kernel)),
        "provenance": "selected_action_to_authenticated_power_herb_standard_charge_terminal_v1",
    }


def _standard_charge_start(
    base: Mapping[str, Any],
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
    readiness: Any,
) -> dict[str, Any]:
    if not isinstance(readiness, Mapping):
        return _result("incomplete", "standard_charge_start_readiness_authority_missing", base)
    materialized = materialize_detached_standard_charge_start(
        strategy_d0=strategy_d0,
        runtime_snapshot=runtime_snapshot,
        action=action,
        actor=actor,
        target=target,
        readiness_authority=readiness,
    )
    if materialized.get("status") != "resolved":
        return _result(
            materialized.get("status", "incomplete"),
            materialized.get("reason", "standard_charge_start_unavailable"),
            base,
        )
    for key in (
        "session_id", "source_runtime_fingerprint", "source_branch_fingerprint",
        "decision_owner", "actor", "action_id", "move_id",
    ):
        if materialized.get(key) != base.get(key):
            return _result("rejected", "standard_charge_start_binding_mismatch", base)
    if materialized.get("source_target_owner") != base["target"]:
        return _result("rejected", "standard_charge_start_target_binding_mismatch", base)
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "execution_family": "standard_charge_start",
        "probability_owner": "selected_action_only",
        "paths": ({
            "probability": deepcopy(materialized["probability"]),
            "action_leaf": deepcopy(materialized["action_leaf"]),
            "post_action_runtime_snapshot": deepcopy(materialized["post_action_runtime_snapshot"]),
            "detached_charge_lifecycle_context": deepcopy(materialized["detached_charge_lifecycle_context"]),
            "standard_charge_start_result": deepcopy(materialized),
            "pending_action_executed": False,
        },),
        "provenance": "selected_action_to_detached_standard_charge_start_v1",
    }


def _endure(base: Mapping[str, Any], snapshot: Mapping[str, Any], authority: Any) -> dict[str, Any]:
    """Establish only Endure's turn-local survival context; no attack is run."""
    context = materialize_detached_endure_turn_context(authority=authority) if isinstance(authority, Mapping) else {"status": "incomplete", "reason": "endure_turn_survival_authority_missing"}
    if context.get("status") != "resolved":
        return _result(context.get("status", "incomplete"), context.get("reason", "endure_turn_survival_unavailable"), base)
    if any(context.get(key) != base.get(key) for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner")) or context.get("endure_user") != base["actor"] or context.get("endure_action_id") != base["action_id"]:
        return _result("rejected", "endure_turn_survival_binding_mismatch", base)
    return {"status":"resolved","schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"execution_family":"endure_turn_survival","probability_owner":"selected_action_only","paths":({"probability":{"numerator":1,"denominator":1},"post_action_runtime_snapshot":deepcopy(dict(snapshot)),"endure_turn_context":context,"pending_action_executed":False},),"provenance":"selected_action_to_runtime_d0_endure_turn_survival_authority_v1"}

def _direct_heal(base: Mapping[str, Any], snapshot: Mapping[str, Any], authority: Any) -> dict[str, Any]:
    materialized=materialize_detached_direct_heal(execution_authority=authority) if isinstance(authority, Mapping) else {"status":"incomplete", "reason":"direct_heal_execution_authority_missing"}
    if materialized.get("status") != "resolved": return _result(materialized.get("status", "incomplete"), materialized.get("reason", "direct_heal_execution_unavailable"), base)
    if any(materialized.get(k) != base.get(k) for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","actor","action_id","move_id")): return _result("rejected","direct_heal_execution_binding_mismatch",base)
    state=deepcopy(snapshot["state"]); row=state[f"{base['actor']['side']}_side"]["pokemon"][base["actor"]["slot_index"]]; post=materialized["heal"]["post_hp"]
    row["current_hp"]=post; row["fainted"]=post==0
    post_snapshot={"status":"runtime_snapshot_ready","session_id":base["session_id"],"state":state,"state_fingerprint":state_fingerprint(state)}
    d0=freeze_runtime_strategy_d0(runtime_snapshot=post_snapshot,decision_owner=base["actor"])
    if d0.get("status")!="resolved": return _result("incomplete",d0.get("reason","direct_heal_post_state_unavailable"),base)
    return {"status":"resolved","schema_version":SCHEMA_VERSION,**base,"execution_family":"direct_heal","probability_owner":"selected_action_only","paths":({"probability":deepcopy(materialized["probability"]),"action_consequence":materialized,"post_action_runtime_snapshot":post_snapshot,"post_action_strategy_d0":d0},),"provenance":"selected_action_to_existing_direct_heal_materializer_v1"}


def _rest(base: Mapping[str, Any], d0: Mapping[str, Any], snapshot: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the existing atomic Rest owner on this exact detached branch."""
    materialized = materialize_champions_rest(
        strategy_d0=d0, runtime_snapshot=snapshot, actor=base["actor"], action=action,
    )
    if materialized.get("status") != "resolved":
        return _result(materialized.get("status", "incomplete"), materialized.get("reason", "rest_execution_unavailable"), base)
    for key in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint", "decision_owner", "actor", "action_id", "move_id"):
        if materialized.get(key) != base.get(key):
            return _result("rejected", "rest_execution_binding_mismatch", base)
    if materialized.get("rest_applied") is True:
        if validate_champions_rest(materialized).get("status") != "resolved":
            return _result("rejected", "rest_execution_provenance_invalid", base)
        post_snapshot = materialized.get("runtime_snapshot")
        if not isinstance(post_snapshot, Mapping):
            return _result("rejected", "rest_post_action_snapshot_missing", base)
    elif materialized.get("rest_applied") is False:
        # A resolved no-effect result still has a detached continuation view.
        post_snapshot = deepcopy(dict(snapshot))
    else:
        return _result("rejected", "rest_execution_outcome_invalid", base)
    post_d0 = freeze_runtime_strategy_d0(runtime_snapshot=post_snapshot, decision_owner=base["actor"])
    if post_d0.get("status") != "resolved":
        return _result("incomplete", post_d0.get("reason", "rest_post_action_d0_unavailable"), base)
    return {
        "status": "resolved", "schema_version": SCHEMA_VERSION, **base,
        "execution_family": "rest", "probability_owner": "selected_action_only",
        "paths": ({
            "probability": {"numerator": 1, "denominator": 1},
            "action_consequence": deepcopy(materialized),
            "rest_application": deepcopy(materialized),
            "post_action_runtime_snapshot": deepcopy(dict(post_snapshot)),
            "post_action_strategy_d0": post_d0,
        },),
        "provenance": "selected_action_to_existing_champions_rest_materializer_v1",
    }


def _graph(base: Mapping[str, Any], strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], metadata: Mapping[str, Any], authorities: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt the native graph owner without flattening its topology or mass."""
    from llm.advisor_detached_variable_two_to_five_hit_graph_immediate_move_pair import _variable_action_graph, _terminal_sources, _synthetic_terminal_leaf
    execution_d0, execution_snapshot, root = strategy_d0, runtime_snapshot, None
    if strategy_d0.get("decision_owner") != dict(actor):
        root = freeze_detached_actor_neutral_root_predictive_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            opponent_action={**deepcopy(dict(action)), "opponent_actor": deepcopy(dict(actor)), "target": deepcopy(dict(target))},
        )
        if root.get("status") != "resolved":
            return _result(root.get("status", "incomplete"), root.get("reason", "actor_neutral_graph_root_unavailable"), base)
        execution_d0, execution_snapshot = root["predictive_strategy_d0"], root["predictive_runtime_snapshot"]
        derived = _base(execution_d0, execution_snapshot, action, actor, target, metadata)
        if derived is None: return _result("rejected", "actor_neutral_graph_execution_binding_invalid", base)
        base = derived
    graph = _variable_action_graph(
        strategy_d0=execution_d0, runtime_snapshot=execution_snapshot, actor=actor, target=target,
        metadata_authority={"status": "resolved", "metadata": deepcopy(dict(metadata))},
        sturdy_survival_authority=authorities.get("sturdy_survival_authority"),
        focus_sash_survival_authority=authorities.get("focus_sash_survival_authority"),
        endure_turn_context=authorities.get("endure_turn_context"),
    )
    if graph.get("status") != "evaluable":
        return _result(graph.get("status", "incomplete"), graph.get("reason", "native_graph_execution_unavailable"), base)
    sources = _terminal_sources(graph)
    if isinstance(sources, str): return _result("rejected", sources, base)
    paths=[]
    for source in sources:
        leaf = _synthetic_terminal_leaf(first_graph=graph, source=source)
        # A graph-owned internal candidate must never replace the selected
        # action identity in this cross-family contract.
        leaf["candidate_id"] = base["action_id"]
        state = materialize_detached_predictive_intermediate_state(
            strategy_d0=execution_d0, terminal_leaf=leaf, root_predictive_authority=root,
        )
        if state.get("status") != "resolved":
            return _result(state.get("status", "incomplete"), state.get("reason", "native_graph_post_terminal_state_unavailable"), base)
        paths.append({"probability": deepcopy(leaf["probability"]), "native_terminal_source": deepcopy(dict(source)), "action_leaf": leaf, "post_action_state": state})
    return {"status":"resolved", "schema_version":SCHEMA_VERSION, **base,
            "execution_family":"native_graph_multi_hit", "probability_owner":"selected_action_only",
            "native_graph":deepcopy(dict(graph)), "paths":tuple(paths),
            "terminal_representation":"native_graph_with_detached_terminal_state_projection",
            "provenance":"selected_action_to_existing_native_graph_materializer_v1"}


def _atomic_item_swap(base: Mapping[str, Any], strategy_d0: Mapping[str, Any], authority: Any) -> dict[str, Any]:
    """Use the canonical item-swap materializer and its existing leaf adapter."""
    from llm.advisor_immediate_move_vs_move_action_pair import _atomic_item_swap_pair_leaf
    materialized = materialize_detached_atomic_item_swap_status(execution_authority=authority) if isinstance(authority, Mapping) else {"status":"incomplete", "reason":"atomic_item_swap_execution_authority_missing"}
    if materialized.get("status") != "resolved":
        return _result(materialized.get("status", "incomplete"), materialized.get("reason", "atomic_item_swap_execution_unavailable"), base)
    if _binding_mismatch(materialized, base): return _result("rejected", "atomic_item_swap_execution_binding_mismatch", base)
    leaf = _atomic_item_swap_pair_leaf(materialized, strategy_d0)
    if isinstance(leaf, str): return _result("rejected", leaf, base)
    paths = _paths_from_leaves(strategy_d0, (leaf,))
    if isinstance(paths, str): return _result("incomplete", paths, base)
    return _family_result(base, "atomic_item_swap", paths, "selected_action_to_existing_atomic_item_swap_materializer_v1")


def _status_special(base: Mapping[str, Any], strategy_d0: Mapping[str, Any], application: Any) -> dict[str, Any]:
    """Reuse the side-neutral application authority; no pending action is run."""
    from llm.advisor_immediate_move_vs_move_action_pair import _taunt_pair_leaf, _encore_pair_leaf, _disable_pair_leaf
    if not isinstance(application, Mapping): return _result("incomplete", "status_special_application_authority_missing", base)
    if application.get("status") != "resolved": return _result(application.get("status", "incomplete"), application.get("reason", "status_special_application_unavailable"), base)
    if _binding_mismatch(application, base): return _result("rejected", "status_special_application_binding_mismatch", base)
    builder = {"taunt": _taunt_pair_leaf, "encore": _encore_pair_leaf, "disable": _disable_pair_leaf}[base["move_id"]]
    leaf = builder(application, strategy_d0)
    if isinstance(leaf, str): return _result("incomplete", leaf, base)
    paths = _paths_from_leaves(strategy_d0, (leaf,))
    if isinstance(paths, str): return _result("incomplete", paths, base)
    for path in paths:
        # Intermediate HP/item projection remains detached.  This distinct
        # field preserves the authoritative restriction lifecycle without
        # falsely treating it as a current reducer observation.
        path["restriction_lifecycle_consequence"] = deepcopy(dict(application))
    return _family_result(base, f"{base['move_id']}_application", paths, "selected_action_to_existing_status_special_application_v1")


def _paths_from_leaves(strategy_d0: Mapping[str, Any], leaves: Any) -> tuple[dict[str, Any], ...] | str:
    if not isinstance(leaves, (tuple, list)) or not leaves: return "selected_action_terminal_leaves_missing"
    result=[]
    for leaf in leaves:
        if not isinstance(leaf, Mapping): return "selected_action_terminal_leaf_invalid"
        state = materialize_detached_predictive_intermediate_state(strategy_d0=strategy_d0, terminal_leaf=leaf)
        if state.get("status") != "resolved": return state.get("reason", "selected_action_post_state_unavailable")
        result.append({"probability":deepcopy(leaf["probability"]), "action_leaf":deepcopy(dict(leaf)), "post_action_state":state, "resulting_active_owners":deepcopy(state.get("active", {}))})
    return tuple(result)


def _family_result(base: Mapping[str, Any], family: str, paths: tuple[Mapping[str, Any], ...], provenance: str) -> dict[str, Any]:
    return {"status":"resolved", "schema_version":SCHEMA_VERSION, **deepcopy(dict(base)), "execution_family":family,
            "probability_owner":"selected_action_only", "paths":tuple(deepcopy(dict(path)) for path in paths), "provenance":provenance}


def _protection(base: Mapping[str, Any], strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], metadata: Mapping[str, Any], authority: Any) -> dict[str, Any]:
    """Materialize the protection action from frozen pending-action facts.

    The pending action provides only actor/action/metadata binding.  It is
    never passed to an attack ledger here, so a gate consumer cannot cause the
    opposing selection to execute while establishing protection.
    """
    from llm.advisor_immediate_move_vs_move_action_pair import _resolved_protection, _protection_leaf
    if not isinstance(authority, Mapping): return _result("incomplete", "protection_selected_action_authority_missing", base)
    if authority.get("status") != "resolved" or _binding_mismatch(authority, base):
        return _result(authority.get("status", "rejected"), authority.get("reason", "protection_selected_action_binding_mismatch"), base)
    pending = authority.get("pending_action_context")
    success = authority.get("protection_success_authority")
    if not isinstance(pending, Mapping) or pending.get("actor") != base["target"] or not isinstance(pending.get("action_id"), str) or not isinstance(pending.get("move_metadata"), Mapping):
        return _result("rejected", "protection_pending_action_context_binding_mismatch", base)
    setup_kind = authority.get("protection_setup_kind")
    if setup_kind in {"quick_guard", "mat_block"}:
        applicable = authority.get("quick_guard_priority_applicability_authority") if setup_kind == "quick_guard" else authority.get("mat_block_direct_damage_applicability_authority")
        if not isinstance(applicable, Mapping) or applicable.get("status") != "resolved" or applicable.get("outcome") not in {"applies", "not_applicable"}:
            return _result("incomplete", "protection_setup_applicability_unavailable", base)
        paths = _protection_paths(base, runtime_snapshot, authority)
        return _family_result(base, "protection", paths, "selected_action_to_existing_guard_setup_v1")
    if not isinstance(success, Mapping): return _result("incomplete", "protection_success_authority_missing", base)
    pair_base={"session_id":base["session_id"], "source_runtime_fingerprint":base["source_runtime_fingerprint"], "source_branch_fingerprint":base["source_branch_fingerprint"], "decision_owner":deepcopy(base["decision_owner"]), "own_actor":deepcopy(base["target"]), "opponent_actor":deepcopy(base["actor"]), "own_action_id":pending["action_id"], "opponent_action_id":base["action_id"]}
    # The existing projector names its shielding owner `opponent`.  This
    # detached role view is an adapter only; it neither changes D0 nor swaps
    # source identities in the emitted leaf.
    view=deepcopy(dict(strategy_d0)); state=view.get("strategy_state", {}).get("active")
    if not isinstance(state, dict): return _result("rejected", "protection_active_state_missing", base)
    state["self"], state["opponent"] = deepcopy(state.get(base["target"]["side"])), deepcopy(state.get(base["actor"]["side"]))
    effect=_resolved_protection(strategy_d0=view, opponent=base["actor"], own=base["target"], metadata=metadata, success_authority=success)
    if effect.get("status") != "resolved": return _result(effect.get("status", "incomplete"), effect.get("reason", "protection_execution_unavailable"), base)
    leaf=_protection_leaf(pair_base, view, metadata)
    if leaf is None: return _result("incomplete", "protection_post_action_hp_unavailable", base)
    # Restore source actor/target provenance (the role view was local only).
    leaf["provenance"]["attacker"], leaf["provenance"]["target"] = deepcopy(base["actor"]), deepcopy(base["target"])
    paths = _protection_paths(base, runtime_snapshot, authority, effect)
    return _family_result(base, "protection", paths, "selected_action_to_existing_protection_projector_v1")



def _protection_setup_leaf(base: Mapping[str, Any], strategy_d0: Mapping[str, Any], metadata: Mapping[str, Any], authority: Mapping[str, Any]) -> dict[str, Any]:
    active = strategy_d0.get("strategy_state", {}).get("active", {})
    actor_hp = active.get(base["actor"]["side"], {}).get("current_hp")
    target_hp = active.get(base["target"]["side"], {}).get("current_hp")
    if not isinstance(actor_hp, int) or not isinstance(target_hp, int): raise ValueError("protection_setup_hp_missing")
    return {"leaf_id": f"{base['action_id']}:setup", "candidate_id": base["action_id"], "action_type":"protection", "branch_path":("protection_setup",), "probability":{"numerator":1,"denominator":1}, "hit_state":"not_applicable", "critical_state":"not_applicable", "damage_roll":"not_applicable", "consequences":{"own_final_hp":actor_hp,"target_final_hp":target_hp,"target_ko":target_hp==0,"self_fainted":actor_hp==0,"secondary":None,"protection_setup":deepcopy(dict(authority))}, "provenance":{"session_id":base["session_id"],"source_runtime_fingerprint":base["source_runtime_fingerprint"],"source_branch_fingerprint":base["source_branch_fingerprint"],"decision_owner":deepcopy(base["decision_owner"]),"attacker":deepcopy(base["actor"]),"target":deepcopy(base["target"]),"move_id":metadata["move_id"]}}


def _protection_paths(base: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], authority: Mapping[str, Any], effect: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
    """A setup action has no HP/condition effect before the pending attempt."""
    return ({"probability":{"numerator":1,"denominator":1}, "post_action_runtime_snapshot":deepcopy(dict(runtime_snapshot)), "protection_setup":deepcopy(dict(authority)), "protection_consequence":deepcopy(dict(effect)) if isinstance(effect, Mapping) else None, "pending_action_executed":False},)

def _pivot(base: Mapping[str, Any], strategy_d0: Mapping[str, Any], runtime_snapshot: Mapping[str, Any], action: Mapping[str, Any], actor: Mapping[str, Any], target: Mapping[str, Any], metadata: Mapping[str, Any], authorities: Mapping[str, Any]) -> dict[str, Any]:
    """Run only the pivot's attack, then the established continuation owner."""
    from llm.advisor_immediate_move_vs_move_action_pair import _attack_ledger
    from llm.advisor_detached_intermediate_predictive_authority import freeze_detached_intermediate_predictive_authority
    root = None
    if strategy_d0.get("decision_owner") != dict(actor):
        root = freeze_detached_actor_neutral_root_predictive_authority(
            strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
            opponent_action={**deepcopy(dict(action)), "opponent_actor":deepcopy(dict(actor)), "target":deepcopy(dict(target))},
        )
        if root.get("status") != "resolved": return _result(root.get("status", "incomplete"), root.get("reason", "actor_neutral_pivot_root_unavailable"), base)
        strategy_d0, runtime_snapshot = root["predictive_strategy_d0"], root["predictive_runtime_snapshot"]
        derived = _base(strategy_d0, runtime_snapshot, action, actor, target, metadata)
        if derived is None: return _result("rejected", "actor_neutral_pivot_execution_binding_invalid", base)
        base = derived
    ledger = _attack_ledger(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, actor=actor, target=target, metadata_authority={"status":"resolved", "metadata":deepcopy(dict(metadata))}, action=action)
    if ledger.get("status") != "evaluable": return _result(ledger.get("status", "incomplete"), ledger.get("reason", "pivot_attack_unavailable"), base)
    replacements, entries = authorities.get("pivot_replacement_authorities"), authorities.get("pivot_entry_authorities")
    paths=[]
    for leaf in ledger.get("terminal_leaves", ()):
        intermediate=materialize_detached_predictive_intermediate_state(strategy_d0=strategy_d0, terminal_leaf=leaf, root_predictive_authority=root)
        if intermediate.get("status") != "resolved": return _result(intermediate.get("status", "incomplete"), intermediate.get("reason", "pivot_post_attack_state_unavailable"), base)
        replacement = _leaf_authority(replacements, leaf, action)
        continuation = freeze_damage_pivot_continuation_authority(strategy_d0=strategy_d0, action=action, move_metadata=metadata, attack_terminal_leaf=leaf, replacement_authority=replacement)
        if continuation.get("status") in {"incomplete", "rejected"}: return _result(continuation["status"], continuation.get("reason", "pivot_continuation_unavailable"), base)
        path={"probability":deepcopy(leaf["probability"]), "action_leaf":deepcopy(dict(leaf)), "post_action_state":intermediate, "pivot_continuation":continuation}
        if continuation.get("status") == "applies":
            entry=_leaf_authority(entries, leaf, action)
            if not isinstance(entry, Mapping): return _result("incomplete", "pivot_switch_entry_authority_missing", base)
            precursor=freeze_detached_intermediate_predictive_authority(strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot, intermediate_state=intermediate, actor=actor, target=target, move_metadata_authority={"status":"resolved", "metadata":deepcopy(dict(metadata))})
            if precursor.get("status") != "resolved": return _result(precursor.get("status", "incomplete"), precursor.get("reason", "pivot_post_attack_authority_unavailable"), base)
            switched=materialize_detached_damage_pivot_switch(intermediate_authority=precursor, pivot_authority=continuation, entry_authority=entry)
            if switched.get("status") != "resolved": return _result(switched.get("status", "incomplete"), switched.get("reason", "pivot_switch_transition_unavailable"), base)
            path.update({"pivot_transition":switched, "post_action_runtime_snapshot":deepcopy(dict(switched["runtime_snapshot"])), "resulting_active_owner":deepcopy(dict(switched["resulting_active_owner"]))})
        paths.append(path)
    return _family_result(base, "damage_pivot", tuple(paths), "selected_action_to_existing_actor_neutral_pivot_transition_v1")


def _leaf_authority(value: Any, leaf: Mapping[str, Any], action: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping): return None
    if "status" in value: return value
    candidate = value.get(leaf.get("leaf_id"), value.get(action.get("action_id")))
    return candidate if isinstance(candidate, Mapping) else None


def _binding_mismatch(value: Mapping[str, Any], base: Mapping[str, Any]) -> bool:
    required=("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","actor","action_id","move_id")
    return any(value.get(key) != base.get(key) for key in required) or ("target" in value and value.get("target") != base.get("target"))


def _delegated(family: str, value: Any, base: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping): return _result("incomplete", f"{family}_selected_action_execution_authority_missing", base)
    # A future family adapter must present a detached post-action state and
    # preserve these exact bindings.  We refuse opaque pair results here.
    if value.get("status") != "resolved" or any(value.get(k) != base.get(k) for k in ("session_id","source_runtime_fingerprint","source_branch_fingerprint","decision_owner","actor","action_id","move_id")) or not isinstance(value.get("paths"), tuple): return _result("rejected", f"{family}_selected_action_execution_authority_invalid", base)
    return {"status":"resolved","schema_version":SCHEMA_VERSION,**deepcopy(dict(value)),**base,"execution_family":family,"probability_owner":"selected_action_only","provenance":"selected_action_to_family_execution_adapter_v1"}


def _base(d0: Any,snapshot: Any,action: Any,actor: Any,target: Any,meta: Any)->dict[str,Any]|None:
    if not isinstance(d0,Mapping) or d0.get("status")!="resolved" or not isinstance(snapshot,Mapping) or not isinstance(action,Mapping) or not isinstance(actor,Mapping) or not isinstance(target,Mapping) or not isinstance(meta,Mapping): return None
    if runtime_strategy_d0_freshness(strategy_d0=d0,runtime_snapshot=snapshot).get("status")!="current": return None
    move=meta.get("move_id"); active=d0.get("active_owners",{})
    if not isinstance(move,str) or active.get(actor.get("side")) != dict(actor) or active.get(target.get("side")) != dict(target) or actor.get("side")==target.get("side") or not isinstance(action.get("action_id"),str): return None
    return {"session_id":d0["session_id"],"source_runtime_fingerprint":d0["source_runtime_fingerprint"],"source_branch_fingerprint":d0["strategy_preview_fingerprint"],"decision_owner":deepcopy(dict(d0["decision_owner"])),"actor":deepcopy(dict(actor)),"target":deepcopy(dict(target)),"action_id":action["action_id"],"move_id":move}

def _result(status:str,reason:str,base:Mapping[str,Any])->dict[str,Any]: return {"status":status,"schema_version":SCHEMA_VERSION,**deepcopy(dict(base)),"reason":reason}
