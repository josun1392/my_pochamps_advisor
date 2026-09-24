"""In-memory production anchors for the existing strict observed transition replay."""
from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Mapping

from llm.advisor_c6_production_decision_capture import ProductionDecisionCapture
from llm.advisor_offline_decision_point_provenance import _freeze
from llm.advisor_offline_learned_strategy_features import materialize_offline_learned_strategy_feature_rows
from llm.advisor_offline_strategy_transition_replay import materialize_offline_strategy_transition
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0


SCHEMA_VERSION = "c6-production-observed-transition-capture-v1"


@dataclass(frozen=True, slots=True)
class ProductionObservedTransitionCapture:
    decision_capture: ProductionDecisionCapture
    _anchors: dict[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _decision_inputs: dict[str, tuple[dict[str, Any], dict[str, Any]]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _historical_inputs: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _attempts: dict[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _resolved: dict[str, Mapping[str, Any]] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.decision_capture, ProductionDecisionCapture):
            raise ValueError("invalid_decision_capture")

    @property
    def session_id(self) -> str:
        return self.decision_capture.session_id

    @property
    def battle_id(self) -> str:
        return self.decision_capture.battle_id

    def retain_decision_anchor(self, *, opportunity_record: Mapping[str, Any],
                               decision_runtime_snapshot: Mapping[str, Any],
                               decision_turn_number: int) -> Mapping[str, Any]:
        opportunity = self._retained_opportunity(opportunity_record)
        if opportunity is None:
            return _failure("rejected", "opportunity_not_retained")
        boundary = opportunity["certificate"]
        if decision_turn_number != boundary["turn_number"]:
            return _failure("rejected", "decision_turn_mismatch")
        commands = self.decision_capture.command_source.read_snapshot(
            captured_session_id=self.session_id)["command_evidence"]
        if any(command["boundary_id"] == boundary["boundary_id"] for command in commands):
            return _failure("rejected", "command_already_admitted")
        d0 = freeze_runtime_strategy_d0(runtime_snapshot=decision_runtime_snapshot,
                                        decision_owner=boundary["actor"])
        if d0.get("status") != "resolved" or d0.get("session_id") != self.session_id:
            return _failure("rejected", "decision_runtime_d0_unavailable")
        anchor = _freeze({"boundary_id": boundary["boundary_id"], "session_id": self.session_id,
                          "battle_id": self.battle_id, "actor": boundary["actor"],
                          "decision_turn_number": decision_turn_number,
                          "decision_runtime_snapshot": decision_runtime_snapshot,
                          "strategy_d0": d0, "feature_contract": None,
                          "historical_attack_bundles": {}})
        prior = self._anchors.get(boundary["boundary_id"])
        if prior is not None:
            if any(prior[key] != anchor[key] for key in (
                "boundary_id", "session_id", "battle_id", "actor", "decision_turn_number",
                "decision_runtime_snapshot", "strategy_d0")):
                return _failure("rejected", "conflicting_decision_anchor")
            return _freeze({"status": "duplicate", "schema_version": SCHEMA_VERSION, "anchor": prior})
        self._anchors[boundary["boundary_id"]] = anchor
        self._decision_inputs[boundary["boundary_id"]] = (
            deepcopy(dict(decision_runtime_snapshot)), deepcopy(dict(d0)))
        return _freeze({"status": "retained", "schema_version": SCHEMA_VERSION, "anchor": anchor})

    def retain_strategy_evidence(self, *, boundary_id: str, strategy_result: Mapping[str, Any],
                                 exact_outcome_ledgers: Mapping[str, Any],
                                 descriptive_metrics: Mapping[str, Any],
                                 historical_attack_bundles: Mapping[str, Any]) -> Mapping[str, Any]:
        anchor = self._anchors.get(boundary_id)
        if anchor is None:
            return _failure("rejected", "decision_anchor_unavailable")
        commands = self.decision_capture.command_source.read_snapshot(
            captured_session_id=self.session_id)["command_evidence"]
        if any(command["boundary_id"] == boundary_id for command in commands):
            return _failure("rejected", "command_already_admitted")
        runtime_input, d0_input = self._decision_inputs[boundary_id]
        features = materialize_offline_learned_strategy_feature_rows(
            strategy_d0=deepcopy(d0_input), runtime_snapshot=deepcopy(runtime_input),
            strategy_result=strategy_result, exact_outcome_ledgers=exact_outcome_ledgers,
            descriptive_metrics=descriptive_metrics)
        if features.get("status") != "resolved":
            return _failure("rejected", "decision_features_invalid")
        candidates = {row["candidate_id"] for row in features["rows"]}
        if not isinstance(historical_attack_bundles, Mapping) or set(historical_attack_bundles) - candidates:
            return _failure("rejected", "foreign_historical_binding")
        for candidate_id, bundle in historical_attack_bundles.items():
            if (not isinstance(bundle, Mapping) or not isinstance(bundle.get("binding"), Mapping)
                    or bundle.get("ledger") != exact_outcome_ledgers.get(candidate_id)
                    or candidate_id not in candidates or not candidate_id.startswith("attack:")):
                return _failure("rejected", "historical_binding_mismatch")
        updated = _freeze({**anchor, "feature_contract": features,
                           "historical_attack_bundles": historical_attack_bundles})
        if anchor["feature_contract"] is not None:
            return (_freeze({"status": "duplicate", "schema_version": SCHEMA_VERSION, "anchor": anchor})
                    if anchor == updated else _failure("rejected", "conflicting_strategy_evidence"))
        self._anchors[boundary_id] = updated
        self._historical_inputs[boundary_id] = deepcopy(dict(historical_attack_bundles))
        return _freeze({"status": "retained", "schema_version": SCHEMA_VERSION, "anchor": updated})

    def attempt_observed_transition(self, *, boundary_id: str,
                                    observation_snapshot: Mapping[str, Any],
                                    next_runtime_snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
        anchor = self._anchors.get(boundary_id)
        if anchor is None:
            return _failure("rejected", "decision_anchor_unavailable")
        if boundary_id in self._resolved:
            return self._resolved[boundary_id]
        if (not isinstance(observation_snapshot, Mapping)
                or observation_snapshot.get("session_id") != self.session_id
                or not isinstance(next_runtime_snapshot, Mapping)
                or next_runtime_snapshot.get("session_id") != self.session_id):
            return _failure("rejected", "stale_or_foreign_runtime_evidence")
        if anchor["feature_contract"] is None:
            result = _failure("incomplete", "decision_feature_contract_unavailable")
            self._attempts[boundary_id] = result
            return result
        rows = observation_snapshot.get("ordered_observations")
        if not isinstance(rows, (tuple, list)):
            return _failure("rejected", "observation_collection_invalid")
        decision_sequence = anchor["decision_runtime_snapshot"]["state"].get("last_applied_observation_sequence") or 0
        executions = []
        for row in rows:
            if not isinstance(row, Mapping):
                return _failure("rejected", "observation_collection_invalid")
            if (row.get("session_id") != self.session_id
                    or row.get("turn_number") != anchor["decision_turn_number"]
                    or row.get("side") != anchor["actor"]["side"]
                    or row.get("slot_index") != anchor["actor"]["slot_index"]
                    or row.get("pokemon_id") != anchor["actor"]["pokemon_id"]
                    or not isinstance(row.get("observation_sequence"), int)
                    or row["observation_sequence"] <= decision_sequence):
                continue
            if row.get("event_kind") in {"executed_move_observed", "pokemon_switch_observed"}:
                executions.append(row)
        if not executions:
            result = _failure("incomplete", "authenticated_execution_unavailable")
            self._attempts[boundary_id] = result
            return result
        if len(executions) != 1:
            return _failure("rejected", "ambiguous_observed_execution")
        execution = executions[0]
        if execution.get("event_kind") == "executed_move_observed":
            move_id = execution.get("move_id")
            candidate_id = f"attack:{move_id}" if isinstance(move_id, str) else ""
            bundle = self._historical_inputs.get(boundary_id, {}).get(candidate_id)
            binding = bundle.get("binding") if isinstance(bundle, Mapping) else None
            ledger = bundle.get("ledger") if isinstance(bundle, Mapping) else None
        else:
            payload = execution.get("payload")
            incoming = payload.get("switch_in_pokemon_id") if isinstance(payload, Mapping) else None
            candidate_id = f"manual_switch:{incoming}" if isinstance(incoming, str) else ""
            binding = ledger = None
        if candidate_id not in {row["candidate_id"] for row in anchor["feature_contract"]["rows"]}:
            return _failure("rejected", "executed_candidate_not_in_decision_features")
        next_state = next_runtime_snapshot.get("state")
        if not isinstance(next_state, Mapping):
            return _failure("rejected", "next_runtime_snapshot_invalid")
        next_sequence = next_state.get("last_applied_observation_sequence")
        if (not isinstance(next_sequence, int) or isinstance(next_sequence, bool)
                or next_sequence <= decision_sequence
                or next_sequence < execution["observation_sequence"]):
            return _failure("rejected", "next_state_sequence_not_later")
        matching_anchor = [row for row in rows if row.get("observation_sequence") == next_sequence]
        if len(matching_anchor) != 1:
            result = _failure("incomplete", "next_state_observation_unavailable")
            self._attempts[boundary_id] = result
            return result
        runtime_input, _ = self._decision_inputs[boundary_id]
        result = materialize_offline_strategy_transition(
            feature_contract=anchor["feature_contract"], candidate_id=candidate_id,
            decision_runtime_snapshot=deepcopy(runtime_input),
            decision_turn_number=anchor["decision_turn_number"],
            observation_snapshot=observation_snapshot,
            executed_observation_id=execution["observation_id"],
            next_runtime_snapshot=next_runtime_snapshot,
            next_state_observation_id=matching_anchor[0]["observation_id"],
            historical_binding=binding, predictive_ledger=ledger)
        if result["status"] == "resolved":
            self._resolved[boundary_id] = result
        else:
            self._attempts[boundary_id] = result
        return result

    def read_snapshot(self, *, captured_session_id: str, captured_battle_id: str) -> Mapping[str, Any]:
        if captured_session_id != self.session_id or captured_battle_id != self.battle_id:
            return _failure("rejected", "stale_or_foreign_battle")
        return _freeze({"status": "ready", "schema_version": SCHEMA_VERSION,
                        "session_id": self.session_id, "battle_id": self.battle_id,
                        "pending_anchors": tuple(self._anchors[key] for key in sorted(self._anchors)
                                                 if key not in self._resolved),
                        "resolved_transitions": tuple(self._resolved[key] for key in sorted(self._resolved)),
                        "latest_attempts": tuple({"boundary_id": key, "result": self._attempts[key]}
                                                 for key in sorted(self._attempts))})

    def _retained_opportunity(self, value: Any) -> Mapping[str, Any] | None:
        if not isinstance(value, MappingProxyType):
            return None
        opportunities = self.decision_capture.opportunity_source.read_snapshot(
            captured_session_id=self.session_id)["opportunities"]
        matches = [row for row in opportunities if row["certificate"]["boundary_id"] ==
                   value.get("certificate", {}).get("boundary_id")]
        if len(matches) != 1:
            return None
        retained = matches[0]
        return retained if all(value.get(key) == retained[key] for key in (
            "certificate", "channel_source", "context_reference", "legal_action_set")) else None


def _failure(status: str, reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": status, "schema_version": SCHEMA_VERSION, "reason": reason})
