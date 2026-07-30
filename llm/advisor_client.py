"""Thin LLM advisor client used by UI spikes.

This module keeps PySide UI code from importing the script module directly.
The underlying quantitative scenario still lives in ``scripts.spike_advisor``
for the v0.5 spike.
"""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import requests

from core.turn_event import TurnPipelineResult, normalize_turn_pipeline_result
from core.turn_state import TurnSnapshot, normalize_turn_snapshot
from core.champions_legal_item_repository import get_legal_item_status
from llm.advisor_battle_state_context import (
    BATTLE_STATE_CONTEXT_ACTIVE_FIELDS,
    BATTLE_STATE_CONTEXT_ALLOWED_SOURCES,
    BATTLE_STATE_CONTEXT_FIELD_FIELDS,
    BATTLE_STATE_CONTEXT_FIELD_ALLOWED_SOURCES,
    BATTLE_STATE_CONTEXT_FORBIDDEN_FIELDS,
    BATTLE_STATE_CONTEXT_FORBIDDEN_SOURCES,
    BATTLE_STATE_CONTEXT_ITEM_ALLOWED_SOURCES,
    BATTLE_STATE_CONTEXT_SAFETY_NOTES,
    BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
    BATTLE_STATE_CONTEXT_UNSUPPORTED_BOUNDARIES,
    build_battle_state_context_from_ui_selected_state,
    build_current_ability_context_from_confirmations,
    build_current_stat_stage_context_from_confirmations,
    build_current_hp_context_from_confirmations,
    build_deterministic_calculation_context,
    build_final_stat_context_from_confirmations,
    build_current_condition_context_from_confirmations,
    build_item_event_context_from_confirmations,
    normalize_user_confirmed_current_ability,
    normalize_user_confirmed_current_field_state,
    normalize_user_confirmed_current_stat_stage,
    normalize_user_confirmed_current_hp,
    normalize_user_confirmed_final_battle_stat,
    normalize_user_confirmed_current_condition,
    normalize_user_confirmed_battle_format,
    validate_explicit_user_item_event_confirmation,
)
from llm.advisor_opponent_move_context import (
    OPPONENT_MOVE_CONTEXT_ALLOWED_MOVE_FIELDS,
    OPPONENT_MOVE_CONTEXT_CANDIDATE_SOURCES,
    OPPONENT_MOVE_CONTEXT_FORBIDDEN_FIELDS,
    OPPONENT_MOVE_CONTEXT_TRUSTED_KNOWN_SOURCES,
    OPPONENT_MOVE_CONTEXT_UNSUPPORTED_BOUNDARIES,
    build_opponent_move_context,
)
from llm.advisor_turn_order_context import (
    TURN_ORDER_CONTEXT_CONFIDENCE_VALUES,
    TURN_ORDER_CONTEXT_FORBIDDEN_FIELDS,
    TURN_ORDER_CONTEXT_ORDER_HINT_VALUES,
    TURN_ORDER_CONTEXT_PRIORITY_RELATION_VALUES,
    TURN_ORDER_CONTEXT_REQUIRED_UNSUPPORTED,
    TURN_ORDER_CONTEXT_SPEED_RELATION_VALUES,
    build_deterministic_turn_order_context,
)
from llm.advisor_payload_contract import (
    ADVICE_CONTEXT_SIDE_FIELDS,
    ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB,
    ADVICE_ITEM_CONTEXT_GUARD_METADATA,
    ADVICE_ITEM_CONTEXT_KEYS,
    DEBUG_ONLY_REASON_PHRASES,
    TURN_PIPELINE_KNOWN_LIMITATIONS,
    TURN_SNAPSHOT_KNOWN_LIMITATIONS,
)
from llm.advisor_turn_snapshot import try_build_turn_snapshot_from_battle_input
from llm.advisor_turn_events import build_optional_turn_pipeline_for_advice_payload
from llm.token_logger import UNKNOWN_MODEL_OR_UNKNOWN_PRICING, TokenLogger
from llm.advisor_candidate_contract import (
    adapt_provider_recommendation_response,
    build_provider_recommendation_payload,
    build_recommendation_presentation_model,
    complete_recommendation_cycle,
    prepare_ui_recommendation_cycle,
)
from scripts.spike_advisor import (
    DEFAULT_MODEL,
    build_prompt,
    call_gemini,
    collect_battle_data,
)


@dataclass(frozen=True)
class SanitizedSmokeResponseCapture:
    """Non-persistent smoke result after in-memory response evaluation."""

    provider_status: str
    semantic_status: str
    sanitized_summary: str
    response_status: str = "available"
    error_category: str | None = None


_STRUCTURED_PROVIDER_PAYLOAD_KEYS = (
    "request_version", "battle_snapshot_summary", "candidate_exact_set",
    "selectable_candidate_exact_set", "candidate_comparisons", "known_limitations", "guardrails",
)
_STRUCTURED_RESPONSE_KEYS = (
    "recommendation_status", "recommended_move", "recommended_slot_index",
    "primary_reasons", "risks", "alternatives",
)
_GROUNDED_STRUCTURED_RESPONSE_KEYS = (*_STRUCTURED_RESPONSE_KEYS, "grounding")
_MECHANICS_ACK_RESPONSE_KEYS = (*_GROUNDED_STRUCTURED_RESPONSE_KEYS, "mechanics_acknowledgements")
_RANKING_ACK_RESPONSE_KEYS = (*_MECHANICS_ACK_RESPONSE_KEYS, "ranking_acknowledgements")
SAFE_PROVIDER_DIAGNOSTIC_CODES = frozenset({
    "provider_client_initialization_failure",
    "provider_model_not_found",
    "provider_authentication_failure",
    "provider_permission_failure",
    "provider_quota_or_rate_limit",
    "provider_timeout",
    "provider_network_failure",
    "provider_service_unavailable",
    "provider_invalid_request",
    "provider_response_failure",
    "provider_unknown_failure",
    "provider_safety_blocked",
    "provider_response_missing",
    "provider_response_malformed",
    "provider_structured_decode_failed",
    "provider_response_validation_failed",
})
_SAFE_API_ERROR_STATUSES = frozenset({"INVALID_ARGUMENT", "UNAUTHENTICATED", "PERMISSION_DENIED", "NOT_FOUND", "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED", "UNAVAILABLE", "INTERNAL", "UNKNOWN"})
_SAFE_PROVIDER_FAILURE_STAGES = frozenset({"client_initialization", "request_transport", "http_response", "response_parsing"})
_SAFE_PROVIDER_COMPONENTS = frozenset({"generation_config", "response_schema"})
_SAFE_PROVIDER_LOGICAL_FIELDS = frozenset({"mechanics_acknowledgements", "ranking_acknowledgements", "grounding", "response_schema"})
_SAFE_SCHEMA_REASONS = frozenset({"schema_keyword_nullable", "schema_keyword_enum", "schema_keyword_required", "schema_keyword_additional_properties", "schema_keyword_composition", "schema_keyword_collection_bound", "schema_keyword_type", "schema_request_rejected", "diagnostic_insufficient"})
_GROUNDING_V1_ENTRY_KEYS = ("confirmed_facts", "unknown_facts", "evidence_only", "conflicts", "conditional_dependencies")
_GROUNDING_V1_ENTRY_SCHEMAS = {
    "confirmed_facts": {"type": "OBJECT", "properties": {"path": {"type": "STRING"}, "status": {"type": "STRING", "enum": ["known", "known_absent"]}, "authority": {"type": "STRING", "enum": ["runtime"]}, "value": {}}, "required": ["path", "status", "authority"]},
    "unknown_facts": {"type": "OBJECT", "properties": {"path": {"type": "STRING"}, "authority": {"type": "STRING", "enum": ["runtime"]}}, "required": ["path", "authority"]},
    "evidence_only": {"type": "OBJECT", "properties": {"path": {"type": "STRING"}, "authority": {"type": "STRING", "enum": ["evidence", "stale"]}, "source": {"type": "STRING", "enum": ["ui", "user", "observation", "deterministic"]}}, "required": ["path", "authority", "source"]},
    "conflicts": {"type": "OBJECT", "properties": {"path": {"type": "STRING"}, "authority": {"type": "STRING", "enum": ["conflict"]}, "source": {"type": "STRING", "enum": ["ui", "user", "observation"]}}, "required": ["path", "authority", "source"]},
    "conditional_dependencies": {"type": "OBJECT", "properties": {"path": {"type": "STRING"}}, "required": ["path"]},
}
_STRUCTURED_CLAIM_SCHEMA = {"type": "OBJECT", "properties": {"kind": {"type": "STRING", "enum": ["damage", "ko", "hit_chance", "move_order", "self_effect", "dynamic_mechanic", "partial_context", "mechanics"]}, "claim": {"type": "STRING", "description": "For a numeric direct-mechanics claim, include only the exact native scope values and no other digit."}, "mechanics_path": {"type": "STRING", "nullable": True, "description": "Required with numeric direct-mechanics claim: exact candidate mechanics path."}, "numeric_scope": {"type": "STRING", "nullable": True, "enum": ["damage_range", "damage_percent_range", "single_hit_probability"], "description": "Required with numeric direct-mechanics claim; it selects the only native values permitted in claim."}}, "required": ["kind", "claim"]}
_MECHANICS_ACK_SCHEMA = {"type": "OBJECT", "properties": {"slot_index": {"type": "INTEGER"}, "move": {"type": "STRING"}, "mechanics_path": {"type": "STRING"}, "status": {"type": "STRING", "enum": ["known", "insufficient_context", "unsupported_mechanic"]}, "missing_inputs_path": {"type": "STRING", "nullable": True}}, "required": ["slot_index", "move", "mechanics_path", "status", "missing_inputs_path"]}
_RANKING_ACK_SCHEMA = {"type": "OBJECT", "properties": {"slot_index": {"type": "INTEGER"}, "move": {"type": "STRING"}, "comparison_status": {"type": "STRING", "enum": ["rankable", "insufficient_context", "unsupported_mechanic", "unavailable"]}, "rank": {"type": "INTEGER", "nullable": True}, "comparison_reason": {"type": "STRING", "enum": ["deterministic_known_mechanics", "only_rankable_candidate", "mechanics_insufficient_context", "mechanics_unsupported", "candidate_unavailable", "mechanics_unavailable", "mechanics_evidence_unavailable"]}}, "required": ["slot_index", "move", "comparison_status", "rank", "comparison_reason"]}
_STRUCTURED_SEMANTIC_GUIDANCE = (
    "Return only the declared JSON shape. A resolved recommendation must use a selectable exact move and slot pair. "
    "Ground reasons and risks in candidate comparisons, warnings, unavailable reasons, and known limitations. "
    "Never use partial_context for evidence already resolved; do not turn global limitations into candidate-specific missing evidence. "
    "Use partial_context only for an actually unavailable or incomplete field. Each reason or risk must be exactly a kind/claim object: use only the supported claim kinds and a non-empty claim string. Alternatives require selectable exact move+slot pairs and reasons. "
    "Do not invent EVs, IVs, nature, items, abilities, opponent moves, or final stats. Use insufficient_context when evidence is insufficient and no_usable_candidate when none is selectable. "
    "When runtime_advice_state is present it is authoritative current state: unknown is unobserved, not absent, false, zero, full HP, healthy, inactive, or empty; known_absent is confirmed absence; known with value is trusted current state. In that case include required grounding-v1 with schema_version plus confirmed_facts, unknown_facts, evidence_only, conflicts, and conditional_dependencies lists; every list entry requires a non-empty canonical provider-safe path. confirmed_facts and unknown_facts use authority runtime; evidence_only uses authority evidence or stale plus an allowed source; conflicts uses authority conflict plus an allowed source. A confirmed grounding entry must reproduce its runtime fact status and, for known facts, its exact runtime value. UI and unapplied observation evidence cannot override runtime known facts or resolve runtime unknown facts; conflicting stale UI evidence belongs only in evidence_only or conflicts, never in confirmed_facts. Never infer current battle facts from species metadata. State uncertainty or conditional dependence when needed, and never expose runtime_advice_state, fingerprint, CAS, reducer, ledger, session authority, request token, or thread identity."
    "When candidate_comparisons contains mechanics_result, treat it as authoritative deterministic evidence: do not recompute, change, or invent damage, percent, or KO values. When mechanics_comparison is present, its comparison_status, rank, and fixed comparison_reason are deterministic: recommend its unique rank-1 candidate; do not reorder candidates, infer a rank for an unranked candidate, or create a scoring rationale not supplied there. For a multi-candidate mechanics comparison, return exactly one value-free ranking_acknowledgements object for every comparison row, copying only its slot_index, move, comparison_status, rank, and comparison_reason. Multi-candidate recommendation claims are value-free: include no damage, percent, KO, rank, score, or other number and no mechanics_path or numeric_scope; the deterministic selection and ranking_acknowledgements are the only provider-facing ranking references. A numeric mechanics, damage, or KO claim is allowed only for a single known direct-mechanics candidate when it includes mechanics_path for that exact candidate and numeric_scope of damage_range, damage_percent_range, or single_hit_probability; every numeric literal in the claim must reproduce exactly the selected native value or range for that scope. Never calculate an average, midpoint, rounded derivative, new KO category, or mixed-candidate value. This is mandatory: return exactly one mechanics_acknowledgements object for every candidate with mechanics_result, using only slot_index, move, canonical mechanics_path candidate_comparisons.<its slot index in the array>.mechanics_result, its exact status, and missing_inputs_path only when status is insufficient_context (otherwise null). mechanics_acknowledgements is value-free: never include mechanics values or duplicate this link in grounding.evidence_only. For insufficient_context mechanics use partial_context only; do not make a damage, KO, or mechanics claim or any mechanics number."
)


class StructuredProviderError(RuntimeError):
    """Sanitized structured-provider failure that never carries provider detail."""

    def __init__(self, code: str, *, safe_context: Mapping[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.safe_context = sanitize_provider_failure_context(safe_context)


def sanitize_provider_failure_context(context: Mapping[str, Any] | None) -> dict[str, Any]:
    """Retain only fixed provider-failure fields; never retain provider text."""
    if not isinstance(context, Mapping):
        return {}
    result: dict[str, Any] = {}
    status_code = context.get("http_status")
    if isinstance(status_code, int) and not isinstance(status_code, bool) and 100 <= status_code <= 599:
        result["http_status"] = status_code
    for key, allowed in (("api_status", _SAFE_API_ERROR_STATUSES), ("stage", _SAFE_PROVIDER_FAILURE_STAGES), ("component", _SAFE_PROVIDER_COMPONENTS), ("logical_field", _SAFE_PROVIDER_LOGICAL_FIELDS), ("reason", _SAFE_SCHEMA_REASONS)):
        value = context.get(key)
        if isinstance(value, str) and value in allowed:
            result[key] = value
    return result


def _safe_http_error_context(response: Any) -> dict[str, Any]:
    """Extract allowlisted API failure metadata without exposing the error body."""
    context: dict[str, Any] = {"stage": "http_response"}
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int) and not isinstance(status_code, bool):
        context["http_status"] = status_code
    try:
        body = response.json()
    except (TypeError, ValueError, AttributeError):
        return sanitize_provider_failure_context(context)
    error = body.get("error") if isinstance(body, Mapping) else None
    if not isinstance(error, Mapping):
        return sanitize_provider_failure_context(context)
    api_status = error.get("status")
    if isinstance(api_status, str) and api_status in _SAFE_API_ERROR_STATUSES:
        context["api_status"] = api_status
    fragments: list[str] = []
    message = error.get("message")
    if isinstance(message, str):
        fragments.append(message.lower())
    details = error.get("details")
    if isinstance(details, list):
        for detail in details:
            if not isinstance(detail, Mapping):
                continue
            violations = detail.get("fieldViolations")
            if not isinstance(violations, list):
                continue
            for violation in violations:
                if isinstance(violation, Mapping):
                    for key in ("field", "description"):
                        value = violation.get(key)
                        if isinstance(value, str):
                            fragments.append(value.lower())
    joined = " ".join(fragments)
    if "generationconfig" in joined or "generation_config" in joined:
        context["component"] = "generation_config"
    if "responseschema" in joined or "response_schema" in joined:
        context["component"] = "response_schema"
    if "mechanics_acknowledgements" in joined:
        context["logical_field"] = "mechanics_acknowledgements"
    elif "grounding" in joined:
        context["logical_field"] = "grounding"
    elif context.get("component") == "response_schema":
        context["logical_field"] = "response_schema"
    keyword_map = (("nullable", "schema_keyword_nullable"), ("enum", "schema_keyword_enum"), ("additionalproperties", "schema_keyword_additional_properties"), ("required", "schema_keyword_required"), ("oneof", "schema_keyword_composition"), ("anyof", "schema_keyword_composition"), ("allof", "schema_keyword_composition"), ("minitems", "schema_keyword_collection_bound"), ("maxitems", "schema_keyword_collection_bound"), ("type", "schema_keyword_type"))
    for token, reason in keyword_map:
        if token in joined:
            context["reason"] = reason
            break
    if context.get("component") == "response_schema" and "reason" not in context:
        context["reason"] = "schema_request_rejected"
    if context.get("http_status") == 400 and "reason" not in context:
        context["reason"] = "diagnostic_insufficient"
    return sanitize_provider_failure_context(context)


def _provider_http_diagnostic(status_code: Any) -> str:
    """Classify an HTTP boundary without retaining response content."""
    if not isinstance(status_code, int) or isinstance(status_code, bool):
        return "provider_response_failure"
    if status_code == 400:
        return "provider_invalid_request"
    if status_code == 401:
        return "provider_authentication_failure"
    if status_code == 403:
        return "provider_permission_failure"
    if status_code == 404:
        return "provider_model_not_found"
    if status_code in {402, 429}:
        return "provider_quota_or_rate_limit"
    if status_code in {408, 504}:
        return "provider_timeout"
    if 500 <= status_code <= 599:
        return "provider_service_unavailable"
    if 400 <= status_code <= 499:
        return "provider_invalid_request"
    return "provider_response_failure"


def _provider_exception_diagnostic(error: Exception) -> str:
    """Classify client-side requests errors by safe exception family only."""
    if isinstance(error, requests.Timeout):
        return "provider_timeout"
    if isinstance(error, (requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema)):
        return "provider_invalid_request"
    if isinstance(error, requests.RequestException):
        return "provider_network_failure"
    if isinstance(error, (TypeError, ValueError)):
        return "provider_client_initialization_failure"
    return "provider_unknown_failure"


def _mechanics_acknowledgement_item_schema(*, provider_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Keep provider schema representable; parser owns exact dynamic linkage."""
    schema = deepcopy(_MECHANICS_ACK_SCHEMA)
    schema["description"] = "Provider-compatible value-free acknowledgement shape; the strict parser validates exact candidate, path, status, and dependency against deterministic evidence."
    comparisons = provider_payload.get("candidate_comparisons")
    expected = []
    if isinstance(comparisons, list):
        for index, candidate in enumerate(comparisons):
            mechanics = candidate.get("mechanics_result") if isinstance(candidate, Mapping) else None
            status = mechanics.get("status") if isinstance(mechanics, Mapping) else None
            if status in {"known", "insufficient_context", "unsupported_mechanic"}:
                expected.append((f"candidate_comparisons.{index}.mechanics_result", status))
    if len(expected) == 1 and expected[0][1] == "insufficient_context":
        path = expected[0][0]
        schema["properties"]["missing_inputs_path"]["description"] = f"For insufficient_context, use exactly {path}.missing_inputs; otherwise use null."
    return schema


def _direct_mechanics_statuses(*, provider_payload: Mapping[str, Any] | None) -> list[str]:
    """Return only native direct-mechanics statuses for state-aware provider bounds."""
    comparisons = provider_payload.get("candidate_comparisons") if isinstance(provider_payload, Mapping) else None
    return [
        candidate["mechanics_result"].get("status")
        for candidate in comparisons
        if isinstance(candidate, Mapping)
        and isinstance(candidate.get("mechanics_result"), Mapping)
        and candidate["mechanics_result"].get("mechanics_source") == "native_q12_direct_damage"
    ] if isinstance(comparisons, list) else []


def _claim_schema_for_provider_payload(*, provider_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Bound the provider claim shape when every direct-mechanics result is incomplete."""
    schema = deepcopy(_STRUCTURED_CLAIM_SCHEMA)
    statuses = _direct_mechanics_statuses(provider_payload=provider_payload)
    if statuses and all(status == "known" for status in statuses):
        if provider_payload is not None and _payload_has_multi_mechanics_ranking(provider_payload):
            return {
                "type": "OBJECT",
                "properties": {
                    "kind": {"type": "STRING", "enum": ["mechanics"]},
                    "claim": {"type": "STRING", "enum": ["deterministic ranking evidence", "deterministic comparison supports the selected action", "selected action follows deterministic ranking"], "description": "Choose exactly one value-free deterministic ranking explanation. ranking_acknowledgements is authoritative; no damage, percent, KO, score, rank, or other number is permitted."},
                },
                "required": ["kind", "claim"],
            }
        schema["properties"]["kind"] = {"type": "STRING", "enum": ["mechanics"]}
        claim_description = "Known direct-mechanics summary. If numeric, use only exact native scope values and no other digit."
        schema["properties"]["claim"] = {"type": "STRING", "description": claim_description}
        schema["properties"]["mechanics_path"] = {"type": "STRING", "description": "Required exact mechanics path for the recommended known direct candidate."}
        schema["properties"]["numeric_scope"] = {"type": "STRING", "enum": ["damage_range", "damage_percent_range", "single_hit_probability"], "description": "Required selected native scope for the recommended known direct candidate."}
        schema["required"] = ["kind", "claim", "mechanics_path", "numeric_scope"]
    if statuses and all(status == "insufficient_context" for status in statuses):
        schema["properties"] = {
            "kind": {"type": "STRING", "enum": ["partial_context"]},
            "claim": {"type": "STRING", "description": "State only missing deterministic context. Do not include damage, percent, KO, or other mechanics numbers."},
        }
    return schema


def _structured_provider_schema(*, runtime_grounding_required: bool = False, mechanics_grounding_required: bool = False, ranking_acknowledgement_required: bool = False, provider_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    claim_schema = _claim_schema_for_provider_payload(provider_payload=provider_payload)
    direct_statuses = _direct_mechanics_statuses(provider_payload=provider_payload)
    properties = {
        "recommendation_status": {"type": "STRING", "enum": ["resolved", "insufficient_context", "no_usable_candidate"], "description": "resolved needs an exact selectable pair; other statuses have no pair."},
        "recommended_move": {"type": "STRING", "nullable": True, "description": "Exact selectable move identity for resolved only."},
        "recommended_slot_index": {"type": "INTEGER", "nullable": True, "description": "Matching exact selectable slot for resolved only."},
        "primary_reasons": {"type": "ARRAY", "items": claim_schema, "description": "Grounded kind/claim mappings only; no contradictory partial_context."},
        "risks": {"type": "ARRAY", "items": claim_schema, "description": "Grounded warnings, unavailable reasons, or known limitations only."},
        "alternatives": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"move": {"type": "STRING"}, "slot_index": {"type": "INTEGER"}, "reason": claim_schema}, "required": ["move", "slot_index", "reason"]}, "description": "Each alternative is an exact selectable move+slot mapping with a grounded reason."},
    }
    if direct_statuses and all(status == "insufficient_context" for status in direct_statuses):
        properties["recommendation_status"] = {"type": "STRING", "enum": ["insufficient_context"], "description": "All direct mechanics are incomplete; preserve insufficient_context."}
    if runtime_grounding_required or mechanics_grounding_required:
        properties["grounding"] = {
            "type": "OBJECT",
            "properties": {
                "schema_version": {"type": "STRING", "enum": ["grounding-v1"]},
                **{key: {"type": "ARRAY", "items": _GROUNDING_V1_ENTRY_SCHEMAS[key]} for key in _GROUNDING_V1_ENTRY_KEYS},
            },
            "required": ["schema_version", *_GROUNDING_V1_ENTRY_KEYS],
            "description": "Required grounding-v1 authority mapping for runtime_advice_state; entries use only canonical provider-safe paths.",
        }
    if mechanics_grounding_required:
        mechanics_schema = _mechanics_acknowledgement_item_schema(provider_payload=provider_payload) if isinstance(provider_payload, Mapping) else _MECHANICS_ACK_SCHEMA
        if ranking_acknowledgement_required:
            mechanics_schema["properties"]["missing_inputs_path"]["description"] = "For a multi-candidate comparison, always use null; authoritative incomplete status is carried by mechanics_acknowledgements, ranking_acknowledgements, and grounding."
        properties["mechanics_acknowledgements"] = {"type": "ARRAY", "items": mechanics_schema, "description": "Required value-free acknowledgement for every direct mechanics candidate; copy only slot, move, canonical mechanics path, status, and missing-input path when incomplete."}
    if ranking_acknowledgement_required:
        properties["ranking_acknowledgements"] = {"type": "ARRAY", "items": _RANKING_ACK_SCHEMA, "description": "Required value-free acknowledgement for every deterministic multi-move comparison; copy only slot, move, status, rank, and fixed reason."}
    return {
        "type": "OBJECT",
        "properties": properties,
        "required": list(_RANKING_ACK_RESPONSE_KEYS if ranking_acknowledgement_required else _MECHANICS_ACK_RESPONSE_KEYS if mechanics_grounding_required else _GROUNDED_STRUCTURED_RESPONSE_KEYS if runtime_grounding_required else _STRUCTURED_RESPONSE_KEYS),
    }


def _payload_has_mechanics_result(payload: Mapping[str, Any]) -> bool:
    comparisons = payload.get("candidate_comparisons")
    return isinstance(comparisons, list) and any(
        isinstance(candidate, Mapping)
        and isinstance(candidate.get("mechanics_result"), Mapping)
        and candidate["mechanics_result"].get("status") != "not_requested"
        for candidate in comparisons
    )


def _payload_has_multi_mechanics_ranking(payload: Mapping[str, Any]) -> bool:
    comparisons = payload.get("candidate_comparisons")
    return isinstance(comparisons, list) and sum(
        isinstance(candidate, Mapping) and isinstance(candidate.get("mechanics_comparison"), Mapping)
        for candidate in comparisons
    ) >= 2


def _normalized_structured_usage(*, usage_data: Any, model: str) -> dict[str, int | str | bool | None]:
    counters = {}
    invalid = not isinstance(usage_data, Mapping)
    for target, source in (("input_tokens", "promptTokenCount"), ("output_tokens", "candidatesTokenCount"), ("cached_tokens", "cachedContentTokenCount")):
        value = usage_data.get(source) if isinstance(usage_data, Mapping) else None
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            counters[target] = value
        else:
            counters[target] = 0
            invalid = True
    return {**counters, "model": model, "tool": "structured_recommendation", "success": True, "failure_code": "provider_usage_unavailable" if invalid else None}


def call_structured_recommendation_provider(*, provider_payload: Mapping[str, Any], model: str) -> tuple[dict[str, Any], dict[str, int | str]]:
    """Make one structured REST request and return only decoded provider-neutral data."""
    allowed = (set(_STRUCTURED_PROVIDER_PAYLOAD_KEYS), {*_STRUCTURED_PROVIDER_PAYLOAD_KEYS, "runtime_advice_state"})
    if not isinstance(provider_payload, Mapping) or set(provider_payload) not in allowed:
        raise StructuredProviderError("provider_response_validation_failed")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise StructuredProviderError("provider_authentication_failure")
    request_body = {
        "contents": [{"role": "user", "parts": [{"text": _STRUCTURED_SEMANTIC_GUIDANCE + "\n\nDeterministic evidence:\n" + json.dumps(dict(provider_payload), ensure_ascii=False)}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": _structured_provider_schema(runtime_grounding_required="runtime_advice_state" in provider_payload, mechanics_grounding_required=_payload_has_mechanics_result(provider_payload), ranking_acknowledgement_required=_payload_has_multi_mechanics_ranking(provider_payload), provider_payload=provider_payload)},
    }
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key}, json=request_body, timeout=60,
        )
    except (requests.RequestException, TypeError, ValueError) as exc:
        stage = "request_transport" if isinstance(exc, requests.RequestException) else "client_initialization"
        raise StructuredProviderError(_provider_exception_diagnostic(exc), safe_context={"stage": stage}) from None
    if not response.ok:
        context = _safe_http_error_context(response)
        raise StructuredProviderError(_provider_http_diagnostic(context.get("http_status")), safe_context=context)
    try:
        body = response.json()
    except (TypeError, ValueError):
        raise StructuredProviderError("provider_structured_decode_failed") from None
    if not isinstance(body, Mapping):
        raise StructuredProviderError("provider_structured_decode_failed")
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        if isinstance(body.get("promptFeedback"), Mapping):
            raise StructuredProviderError("provider_safety_blocked")
        raise StructuredProviderError("provider_response_missing")
    candidate = candidates[0]
    if not isinstance(candidate, Mapping):
        raise StructuredProviderError("provider_response_malformed")
    if candidate.get("finishReason") == "SAFETY":
        raise StructuredProviderError("provider_safety_blocked")
    content = candidate.get("content")
    parts = content.get("parts") if isinstance(content, Mapping) else None
    text = parts[0].get("text") if isinstance(parts, list) and parts and isinstance(parts[0], Mapping) else None
    if not isinstance(text, str) or not text.strip():
        raise StructuredProviderError("provider_response_missing")
    if text.lstrip().startswith("```"):
        raise StructuredProviderError("provider_response_malformed")
    try:
        decoded = json.loads(text)
    except (TypeError, ValueError):
        raise StructuredProviderError("provider_structured_decode_failed") from None
    expected_response_keys = _RANKING_ACK_RESPONSE_KEYS if _payload_has_multi_mechanics_ranking(provider_payload) else _MECHANICS_ACK_RESPONSE_KEYS if _payload_has_mechanics_result(provider_payload) else _GROUNDED_STRUCTURED_RESPONSE_KEYS if "runtime_advice_state" in provider_payload else _STRUCTURED_RESPONSE_KEYS
    if not isinstance(decoded, dict) or set(decoded) != set(expected_response_keys):
        raise StructuredProviderError("provider_response_malformed")
    usage = _normalized_structured_usage(usage_data=body.get("usageMetadata"), model=model)
    return deepcopy(decoded), usage


def format_recommendation_presentation_text(*, presentation_model: Mapping[str, Any]) -> str:
    """Format only validated presentation fields for the existing text panel."""
    if not isinstance(presentation_model, Mapping):
        return "추천 응답 검증에 실패했습니다."
    status = presentation_model.get("status")
    if status == "preparation_not_ready":
        return "추천을 확정할 정보가 부족합니다."
    if status == "resolved":
        lines = [f"추천 기술: {presentation_model.get('recommended_move')}", f"슬롯: {presentation_model.get('recommended_slot_index')}"]
        for label, key in (("주요 이유", "primary_reasons"), ("위험 요소", "risks"), ("대안", "alternatives"), ("후보 요약", "candidate_summaries")):
            values = presentation_model.get(key, [])
            lines.append(f"{label}: {len(values)}" if isinstance(values, list) and values else f"{label}: 없음")
        return "\n".join(lines)
    if status == "insufficient_context":
        return "추천을 확정할 정보가 부족합니다."
    if status == "no_usable_candidate":
        return "사용 가능한 후보 기술이 없습니다."
    if status in SAFE_PROVIDER_DIAGNOSTIC_CODES:
        return "제공자 호출에 실패했습니다."
    return "추천 응답 검증에 실패했습니다."


def _log_structured_recommendation_usage(*, model: str, usage: Mapping[str, Any], status: str) -> dict[str, Any]:
    """Log approved usage metadata only; logging failure is sanitized and non-fatal."""
    try:
        logger = TokenLogger()
        logger.log_call(
            model=model,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            cached_tokens=int(usage.get("cached_tokens", 0)),
            tool_name="structured_recommendation",
            turn_number=1,
            game_id="ui_structured_recommendation_v14_9",
        )
        return {"logging_status": "recorded", "recommendation_status": status}
    except Exception:
        return {"logging_status": "failed", "recommendation_status": status}


def run_structured_ui_recommendation(*, selected_moves: Any, battle_input: Mapping[str, Any], move_repository: Any, species_repository: Any = None, model: str | None = None, usage_logging_enabled: bool = False, observation_snapshot: Mapping[str, Any] | None = None, trusted_turn_context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Separate structured coexistence flow; it never falls back to legacy advice."""
    prepared = prepare_ui_recommendation_cycle(selected_moves=selected_moves, battle_input=battle_input, move_repository=move_repository, species_repository=species_repository, observation_snapshot=observation_snapshot, trusted_turn_context=trusted_turn_context)
    if prepared.get("status") != "ready":
        presentation = build_recommendation_presentation_model(completed_cycle={"status": "response_validation_failed", "candidates": prepared.get("candidates", []), "errors": ["preparation_not_ready"]})
        return {"status": "preparation_not_ready", "prepared_cycle": deepcopy(prepared), "completed_cycle": None, "presentation_model": presentation, "usage": {}, "errors": ["preparation_not_ready"]}
    payload = build_provider_recommendation_payload(prepared_cycle=prepared)
    if payload.get("status"):
        return {"status": "provider_response_validation_failed", "prepared_cycle": deepcopy(prepared), "completed_cycle": None, "presentation_model": build_recommendation_presentation_model(completed_cycle={"status": "response_validation_failed", "candidates": prepared.get("candidates", []), "errors": ["provider_response_validation_failed"]}), "usage": {}, "errors": ["provider_response_validation_failed"]}
    try:
        decoded, usage = call_structured_recommendation_provider(provider_payload=payload, model=model or DEFAULT_MODEL)
    except StructuredProviderError as error:
        return {"status": error.code, "prepared_cycle": deepcopy(prepared), "completed_cycle": None, "presentation_model": build_recommendation_presentation_model(completed_cycle={"status": "response_validation_failed", "candidates": prepared.get("candidates", []), "errors": [error.code]}), "usage": {}, "errors": [error.code]}
    adapted = adapt_provider_recommendation_response(provider_response=decoded)
    if adapted.get("status") == "provider_response_validation_failed":
        return {"status": "provider_response_validation_failed", "prepared_cycle": deepcopy(prepared), "completed_cycle": None, "presentation_model": build_recommendation_presentation_model(completed_cycle={"status": "response_validation_failed", "candidates": prepared.get("candidates", []), "errors": ["provider_response_validation_failed"]}), "usage": deepcopy(usage), "errors": ["provider_response_validation_failed"]}
    completed = complete_recommendation_cycle(prepared_cycle=prepared, response_payload=adapted)
    presentation = build_recommendation_presentation_model(completed_cycle=completed)
    logging_summary = _log_structured_recommendation_usage(model=model or DEFAULT_MODEL, usage=usage, status=completed["status"]) if usage_logging_enabled else {"logging_status": "not_recorded", "recommendation_status": completed["status"]}
    return {"status": completed["status"], "prepared_cycle": deepcopy(prepared), "completed_cycle": deepcopy(completed), "presentation_model": presentation, "usage": deepcopy(usage), "logging_summary": logging_summary, "errors": list(completed.get("errors", []))}


def run_spike_advice(model: str | None = None) -> tuple[str, dict[str, int], dict[str, Any]]:
    """Run the hardcoded v0.5 advisor spike and return recommendation + usage.

    Returns:
        ``(recommendation_text, usage, session_summary)``.
    """
    selected_model = model or DEFAULT_MODEL
    data = collect_battle_data()
    prompt = build_prompt(data)
    recommendation, usage = call_gemini(prompt, selected_model)

    logger = TokenLogger()
    try:
        logger.log_call(
            model=selected_model,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
            tool_name="damage_calculator",
            turn_number=1,
            game_id="spike_mega_kangaskhan_vs_garchomp",
        )
        summary = logger.get_session_summary()
    except Exception as exc:  # pragma: no cover - defensive UI resilience path
        summary = {
            "total_calls": 0,
            "total_input_tokens": usage.get("input_tokens", 0),
            "total_output_tokens": usage.get("output_tokens", 0),
            "total_cached_tokens": usage.get("cached_tokens", 0),
            "estimated_cost_usd": 0.0,
            "pricing_status": UNKNOWN_MODEL_OR_UNKNOWN_PRICING,
            "pricing_status_counts": {UNKNOWN_MODEL_OR_UNKNOWN_PRICING: 1},
            "by_tool": {},
            "token_logging_error": str(exc),
        }

    return recommendation, usage, summary


def build_ui_advice_payload(
    battle_input: dict[str, Any],
    turn_snapshot: TurnSnapshot | dict[str, Any] | None = None,
    turn_pipeline: TurnPipelineResult | dict[str, Any] | None = None,
    turn_order_context: dict[str, Any] | None = None,
    opponent_move_context: dict[str, Any] | None = None,
    battle_state_context: dict[str, Any] | None = None,
    item_event_context: dict[str, Any] | None = None,
    condition_context: dict[str, Any] | None = None,
    ability_context: dict[str, Any] | None = None,
    stat_stage_context: dict[str, Any] | None = None,
    final_stat_context: dict[str, Any] | None = None,
    field_state_context: dict[str, Any] | None = None,
    current_hp_context: dict[str, Any] | None = None,
    battle_format_context: dict[str, Any] | None = None,
    deterministic_calculation_context: dict[str, Any] | None = None,
    *,
    enable_turn_order_context: bool = False,
    enable_opponent_move_context: bool = False,
    enable_battle_state_context: bool = False,
    enable_item_event_context: bool = False,
    enable_condition_context: bool = False,
    enable_ability_context: bool = False,
    enable_stat_stage_context: bool = False,
    enable_final_stat_context: bool = False,
    enable_field_state_context: bool = False,
    enable_current_hp_context: bool = False,
    enable_battle_format_context: bool = False,
    enable_deterministic_calculation_context: bool = False,
) -> dict[str, Any]:
    """Return the Gemini default-advice payload without debug-only item context."""
    payload = deepcopy(battle_input)
    filtered_payload = filter_context_for_default_advice(payload)
    _add_observed_previous_damage_context_to_advice_payload(
        filtered_payload, enable_observed_previous_damage_context=enable_battle_state_context
    )
    _add_turn_snapshot_to_advice_payload(filtered_payload, turn_snapshot)
    _add_turn_pipeline_to_advice_payload(filtered_payload, turn_pipeline)
    _add_turn_order_context_to_advice_payload(
        filtered_payload,
        turn_order_context,
        enable_turn_order_context=enable_turn_order_context,
    )
    _add_opponent_move_context_to_advice_payload(
        filtered_payload,
        opponent_move_context,
        enable_opponent_move_context=enable_opponent_move_context,
    )
    _add_battle_state_context_to_advice_payload(
        filtered_payload,
        battle_state_context,
        enable_battle_state_context=enable_battle_state_context,
    )
    _add_item_event_context_to_advice_payload(
        filtered_payload,
        item_event_context,
        enable_item_event_context=enable_item_event_context,
    )
    _add_condition_context_to_advice_payload(
        filtered_payload,
        condition_context,
        enable_condition_context=enable_condition_context,
    )
    _add_ability_context_to_advice_payload(
        filtered_payload,
        ability_context,
        enable_ability_context=enable_ability_context,
    )
    _add_stat_stage_context_to_advice_payload(filtered_payload, stat_stage_context, enable_stat_stage_context=enable_stat_stage_context)
    _add_final_stat_context_to_advice_payload(filtered_payload, final_stat_context, enable_final_stat_context=enable_final_stat_context)
    _add_field_state_context_to_advice_payload(
        filtered_payload,
        field_state_context,
        enable_field_state_context=enable_field_state_context,
    )
    _add_current_hp_context_to_advice_payload(filtered_payload, current_hp_context, enable_current_hp_context=enable_current_hp_context)
    _add_battle_format_context_to_advice_payload(
        filtered_payload, battle_format_context, enable_battle_format_context=enable_battle_format_context
    )
    _add_deterministic_calculation_context_to_advice_payload(
        filtered_payload,
        deterministic_calculation_context,
        enable_deterministic_calculation_context=enable_deterministic_calculation_context,
    )
    return filtered_payload


def filter_context_for_default_advice(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove debug-only item context from the Gemini default-advice payload."""
    _remove_ui_only_field_profiles(payload)
    available_item_sides = _collect_available_item_context_sides(payload)
    _hide_move_local_unavailable_type_boost_item_effects(payload)
    hidden_item_sides = _remove_unavailable_item_contexts(payload)
    hidden_item_sides -= available_item_sides
    hidden_item_ids = _hide_advice_hidden_item_profiles(payload, hidden_item_sides)
    _hide_advice_hidden_item_effects(payload, hidden_item_ids)
    _remove_debug_only_limitations(payload)
    return payload


def _remove_ui_only_field_profiles(payload: dict[str, Any]) -> None:
    payload.pop("field_profiles", None)
    payload.pop("item_event_confirmations", None)
    payload.pop("current_condition_confirmations", None)
    payload.pop("current_ability_confirmations", None)
    payload.pop("current_stat_stage_confirmations", None)
    payload.pop("current_final_stat_confirmations", None)
    payload.pop("current_hp_confirmations", None)
    payload.pop("current_field_state_confirmation", None)
    payload.pop("current_battle_format_confirmation", None)


def run_ui_selected_advice(
    battle_input: dict[str, Any],
    model: str | None = None,
    *,
    enable_turn_pipeline: bool = False,
    enable_turn_order_context: bool = False,
    enable_opponent_move_context: bool = False,
    enable_battle_state_context: bool = False,
) -> tuple[str, dict[str, int], dict[str, Any]]:
    """Run the v0.6 UI-selected Pokemon advisor flow.

    The caller passes plain dictionaries collected from UI state. This function
    owns prompt construction, Gemini invocation, and token logging.
    """
    selected_model = model or DEFAULT_MODEL
    turn_snapshot = try_build_turn_snapshot_from_battle_input(battle_input)
    prompt = _build_ui_selected_prompt(
        battle_input,
        turn_snapshot=turn_snapshot,
        enable_turn_pipeline=enable_turn_pipeline,
        enable_turn_order_context=enable_turn_order_context,
        enable_opponent_move_context=enable_opponent_move_context,
        enable_battle_state_context=enable_battle_state_context,
    )
    recommendation, usage = call_gemini(prompt, selected_model)
    summary = _log_advisor_call(
        model=selected_model,
        usage=usage,
        game_id="ui_selected_pokemon_v0_6",
    )
    return recommendation, usage, summary


def run_ui_selected_advice_with_sanitized_smoke_capture(
    battle_input: dict[str, Any],
    response_evaluator: Callable[[str], tuple[str, str]],
    model: str | None = None,
    *,
    enable_turn_pipeline: bool = False,
    enable_turn_order_context: bool = False,
    enable_opponent_move_context: bool = False,
    enable_battle_state_context: bool = False,
) -> tuple[SanitizedSmokeResponseCapture, dict[str, int], dict[str, Any]]:
    """Evaluate an advice response in memory without persisting its raw text.

    Provider exceptions intentionally propagate so smoke callers can classify
    them separately from a successful provider call whose evaluator is unable
    to produce a semantic result.
    """
    recommendation, usage, summary = run_ui_selected_advice(
        battle_input,
        model=model,
        enable_turn_pipeline=enable_turn_pipeline,
        enable_turn_order_context=enable_turn_order_context,
        enable_opponent_move_context=enable_opponent_move_context,
        enable_battle_state_context=enable_battle_state_context,
    )
    if not isinstance(recommendation, str) or not recommendation.strip():
        semantic_status = "response_unavailable"
        sanitized_summary = "Provider response text was unavailable for semantic evaluation."
        response_status = "unavailable"
        error_category = "response_unavailable"
    else:
        try:
            semantic_status, sanitized_summary = response_evaluator(recommendation)
            response_status = "available"
            error_category = None
        except Exception:
            semantic_status = "response_unavailable"
            sanitized_summary = "Semantic evaluator did not produce a result."
            response_status = "available"
            error_category = "evaluator_failure"

    if semantic_status not in {"pass", "fail", "response_unavailable"}:
        raise ValueError("smoke evaluator returned an unsupported semantic status")
    if not isinstance(sanitized_summary, str):
        raise ValueError("smoke evaluator summary must be a string")
    sanitized_summary = " ".join(sanitized_summary.split())[:240]
    if recommendation and recommendation in sanitized_summary:
        raise ValueError("smoke evaluator summary must not contain the full provider response")
    return (
        SanitizedSmokeResponseCapture(
            provider_status="provider_success",
            semantic_status=semantic_status,
            sanitized_summary=sanitized_summary,
            response_status=response_status,
            error_category=error_category,
        ),
        usage,
        summary,
    )


def _build_ui_selected_prompt(
    battle_input: dict[str, Any],
    turn_snapshot: TurnSnapshot | dict[str, Any] | None = None,
    turn_pipeline: TurnPipelineResult | dict[str, Any] | None = None,
    turn_order_context: dict[str, Any] | None = None,
    opponent_move_context: dict[str, Any] | None = None,
    battle_state_context: dict[str, Any] | None = None,
    item_event_context: dict[str, Any] | None = None,
    condition_context: dict[str, Any] | None = None,
    ability_context: dict[str, Any] | None = None,
    stat_stage_context: dict[str, Any] | None = None,
    final_stat_context: dict[str, Any] | None = None,
    field_state_context: dict[str, Any] | None = None,
    current_hp_context: dict[str, Any] | None = None,
    deterministic_calculation_context: dict[str, Any] | None = None,
    *,
    enable_turn_pipeline: bool = False,
    enable_turn_order_context: bool = False,
    enable_opponent_move_context: bool = False,
    enable_battle_state_context: bool = False,
) -> str:
    observed_previous_damage_context = None
    if enable_battle_state_context and isinstance(battle_input.get("observed_previous_damage_confirmation"), dict):
        try:
            observed_previous_damage_context = normalize_observed_previous_damage_confirmation(battle_input["observed_previous_damage_confirmation"])
        except ValueError:
            observed_previous_damage_context = None
    if turn_pipeline is None and enable_turn_pipeline:
        base_payload = build_ui_advice_payload(
            battle_input,
            turn_snapshot=turn_snapshot,
        )
        selected_move = _selected_move_payload_from_advice_payload(base_payload)
        turn_pipeline = build_optional_turn_pipeline_for_advice_payload(
            base_payload,
            enable_turn_pipeline=True,
            selected_move_id=_string_field(selected_move, "move_id"),
            damage_estimate_ref=_move_payload_ref(selected_move, "damage_estimate"),
            ko_context_ref=_move_payload_ref(selected_move, "ko_context"),
        )

    if turn_order_context is None and enable_turn_order_context:
        base_payload = build_ui_advice_payload(
            battle_input,
            turn_snapshot=turn_snapshot,
        )
        turn_order_context = _build_optional_turn_order_context_for_advice_payload(base_payload)

    if opponent_move_context is None and enable_opponent_move_context:
        base_payload = build_ui_advice_payload(
            battle_input,
            turn_snapshot=turn_snapshot,
        )
        opponent_move_context = _build_optional_opponent_move_context_for_advice_payload(base_payload)

    if battle_state_context is None and enable_battle_state_context:
        battle_state_context = build_battle_state_context_from_ui_selected_state(
            battle_input,
            include_user_confirmed_items=enable_battle_state_context,
            include_user_confirmed_fields=enable_battle_state_context,
        )

    if item_event_context is None and enable_battle_state_context:
        item_event_context = build_item_event_context_from_confirmations(
            battle_input.get("item_event_confirmations")
        )

    if condition_context is None and enable_battle_state_context:
        condition_context = build_current_condition_context_from_confirmations(
            battle_input.get("current_condition_confirmations")
        )

    if ability_context is None and enable_battle_state_context:
        ability_context = build_current_ability_context_from_confirmations(
            battle_input.get("current_ability_confirmations")
        )
    if stat_stage_context is None and enable_battle_state_context:
        stat_stage_context = build_current_stat_stage_context_from_confirmations(
            battle_input.get("current_stat_stage_confirmations")
        )
    if final_stat_context is None and enable_battle_state_context:
        final_stat_context = build_final_stat_context_from_confirmations(
            battle_input.get("current_final_stat_confirmations")
        )
    if current_hp_context is None and enable_battle_state_context:
        current_hp_context = build_current_hp_context_from_confirmations(battle_input.get("current_hp_confirmations"))
    if field_state_context is None and enable_battle_state_context:
        raw_field_state = battle_input.get("current_field_state_confirmation")
        if isinstance(raw_field_state, dict):
            try:
                field_state_context = {
                    "current_field": normalize_user_confirmed_current_field_state(raw_field_state)
                }
            except ValueError:
                field_state_context = None
    battle_format_context = None
    if enable_battle_state_context:
        raw_battle_format = battle_input.get("current_battle_format_confirmation")
        if isinstance(raw_battle_format, dict):
            try:
                battle_format_context = {
                    "current_battle_format": normalize_user_confirmed_battle_format(raw_battle_format)
                }
            except ValueError:
                battle_format_context = None
    if deterministic_calculation_context is None and enable_battle_state_context:
        deterministic_calculation_context = build_deterministic_calculation_context(
            final_stat_context,
            stat_stage_context,
            _selected_move_payload_from_advice_payload(battle_input),
            current_hp_context,
            battle_input.get("pokemon"),
            condition_context,
            field_state_context,
            battle_format_context,
            _selected_opponent_move_payload_from_advice_payload(battle_input),
            battle_input.get("attacker_level_confirmation") if isinstance(battle_input.get("attacker_level_confirmation"), dict) else None,
            observed_previous_damage_context,
            battle_input.get("battle_counter_confirmation") if isinstance(battle_input.get("battle_counter_confirmation"), dict) else None,
            battle_input.get("consecutive_use_confirmation") if isinstance(battle_input.get("consecutive_use_confirmation"), dict) else None,
        )

    advice_payload = build_ui_advice_payload(
        battle_input,
        turn_snapshot=turn_snapshot,
        turn_pipeline=turn_pipeline,
        turn_order_context=turn_order_context,
        opponent_move_context=opponent_move_context,
        battle_state_context=battle_state_context,
        item_event_context=item_event_context,
        condition_context=condition_context,
        ability_context=ability_context,
        stat_stage_context=stat_stage_context,
        final_stat_context=final_stat_context,
        field_state_context=field_state_context,
        current_hp_context=current_hp_context,
        battle_format_context=battle_format_context,
        deterministic_calculation_context=deterministic_calculation_context,
        enable_turn_order_context=enable_turn_order_context,
        enable_opponent_move_context=enable_opponent_move_context,
        enable_battle_state_context=enable_battle_state_context,
        enable_item_event_context=enable_battle_state_context,
        enable_condition_context=enable_battle_state_context,
        enable_ability_context=enable_battle_state_context,
        enable_stat_stage_context=enable_battle_state_context,
        enable_final_stat_context=enable_battle_state_context,
        enable_field_state_context=enable_battle_state_context,
        enable_current_hp_context=enable_battle_state_context,
        enable_battle_format_context=enable_battle_state_context,
        enable_deterministic_calculation_context=enable_battle_state_context,
    )
    available_item_context_guard = _build_available_item_context_required_mention_guard(advice_payload)
    turn_snapshot_guard = _build_turn_snapshot_prompt_guard(advice_payload)
    turn_pipeline_guard = _build_turn_pipeline_prompt_guard(advice_payload)
    turn_order_context_guard = _build_turn_order_context_prompt_guard(advice_payload)
    opponent_move_context_guard = _build_opponent_move_context_prompt_guard(advice_payload)
    battle_state_context_guard = _build_battle_state_context_prompt_guard(advice_payload)
    item_event_context_guard = _build_item_event_context_prompt_guard(advice_payload)
    condition_context_guard = _build_condition_context_prompt_guard(advice_payload)
    ability_context_guard = _build_ability_context_prompt_guard(advice_payload)
    stat_stage_context_guard = _build_stat_stage_context_prompt_guard(advice_payload)
    final_stat_context_guard = _build_final_stat_context_prompt_guard(advice_payload)
    deterministic_calculation_context_guard = _build_deterministic_calculation_context_prompt_guard(advice_payload)
    current_hp_context_guard = _build_current_hp_context_prompt_guard(advice_payload)
    field_state_context_guard = _build_field_state_context_prompt_guard(advice_payload)
    context_attribution_guard = _build_condition_item_event_attribution_prompt_guard(advice_payload)
    structured_acknowledgement_guard = _build_structured_trusted_context_acknowledgement_prompt_guard(advice_payload)
    return (
        "You are Master Ball Advisor. Recommend the best one-turn action using "
        "only the selected Pokemon identity and UI state below. Be concise, "
        "name the recommended direction, and mention the main limitation in the "
        "data. "
        f"{turn_snapshot_guard}"
        f"{turn_pipeline_guard}"
        f"{turn_order_context_guard}"
        f"{opponent_move_context_guard}"
        f"{battle_state_context_guard}"
        f"{item_event_context_guard}"
        f"{condition_context_guard}"
        f"{ability_context_guard}"
        f"{stat_stage_context_guard}"
        f"{final_stat_context_guard}"
        f"{deterministic_calculation_context_guard}"
        f"{current_hp_context_guard}"
        f"{field_state_context_guard}"
        f"{context_attribution_guard}"
        f"{structured_acknowledgement_guard}"
        "If a damage_estimate is present, use it only under its stated "
        "assumption_profile and never describe it as final battle damage. Do "
        "not claim OHKO, 2HKO, KO chance, survival, or speed order unless those "
        "fields are explicitly provided. If ko_context is present, treat it as "
        "limited damage-roll context only, not final battle truth. ko_context "
        "does not change raw damage_range or rolls; OHKO chance is based on "
        "damage rolls only, and 2HKO context is a limited min/max estimate, "
        "not final turn simulation. ko_context does not model accuracy, speed "
        "order, priority, recovery, hazards, chip damage, switching, protection, "
        "or turn sequencing. survival_context is separate from raw "
        "ko_context and is not included in KO probability. If opponent_moves is present, treat "
        "known_moves as user-confirmed and candidate_moves only as possible, "
        "not confirmed, opponent moves. You may mention candidate moves as "
        "possible threats, but label them as unconfirmed. Opponent known move "
        "damage estimates, when present, are rough default-assumption threat "
        "references against my_active. User-confirmed final stats may be used "
        f"{available_item_context_guard}"
        "when stat_profiles provides them, but do not infer EVs, IVs, nature, "
        "items, or speed order from final stats. If speed_context is present, "
        "treat it as raw/effective Speed comparison only, not final turn order. If "
        "speed_context.is_final_turn_order is false, do not say a Pokemon will "
        "move first or that turn order is guaranteed. Use wording such as "
        "based on raw Speed only or appears faster by raw Speed. Default Speed "
        "fallback is not used in v0.30; raw/effective Speed comparison requires "
        "user-confirmed final Speed for both active Pokemon. If effective_speed "
        "is present, treat it as a supported speed modifier estimate, not final "
        "turn order. Choice Scarf speed may be included only when speed_context "
        "marks it applied from a user-confirmed item; for Choice Scarf, choice "
        "lock is still not modeled. If raw Speed and effective Speed disagree, explain the "
        "difference without saying turn order is guaranteed. Do not apply "
        "priority, Tailwind, Trick Room, paralysis, Speed stages, or ability "
        "speed effects unless explicit calculated fields say they are modeled. "
        "Quick Claw speed-order context may appear only as limited "
        "speed_order_context. speed_order_context applies only when Quick "
        "Claw is user-confirmed and Champions legal. It may say Quick Claw "
        "may affect move order or can occasionally affect move order, but "
        "move order is not fully modeled and this is not guaranteed priority. "
        "Final move order, activation probability, speed ties, priority, "
        "Trick Room, Tailwind, paralysis, boosts, abilities, weather, item "
        "consumption, and turn sequencing are not modeled. Do not say will "
        "move first, guaranteed outspeeds, confirmed first, always acts "
        "before, wins the speed interaction, or safe because it moves first "
        "from speed_order_context. If speed_order_context is unavailable, "
        "treat the reason as developer/debug/contract metadata only and do "
        "not mention the item name, effect, or unavailable reason in default "
        "advice unless the user explicitly asks. Choice Scarf is not modeled "
        "through speed_order_context; keep Choice Scarf in speed_context. "
        "If item_profiles is present, "
        "distinguish unknown, none, system_default_none, and user_confirmed "
        "items. Only item effects marked as applied in "
        "damage_estimate.item_effects are included in damage numbers. Legal "
        "items and modeled item effects are separate concepts: a "
        "legal_but_not_modeled selected item may be user-confirmed, but its "
        "effect is not included unless item_effects marks it applied. "
        "For type boosting items, say the damage modifier is included only "
        "when damage_estimate.item_effects.attacker_item.status is applied; "
        "do not say a type boosting item boosted damage when the move type "
        "does not match or the item is unsupported. Legal item selection does "
        "not imply the selected item has a modeled effect. Fairy Feather is "
        "legal but not damage-modeled until a catalog-backed modifier exists. "
        "Type-boost item context may appear only as limited type_boost_context. "
        "type_boost_context is an advice context for user-confirmed, Champions "
        "legal, damage-supported type-boosting items when the move type matches "
        "the boosted type. It does not change raw damage_range or rolls beyond "
        "the existing damage_estimate.item_effects calculation, and ko_context "
        "is unchanged by type_boost_context. Type-boost-adjusted KO/OHKO/2HKO "
        "context is not calculated. Do not say boosted damage guarantees KO, "
        "secures the KO, proves the KO, or is final battle damage. If "
        "type_boost_context is unavailable, treat the reason as developer/"
        "debug/contract metadata only and do not mention the item name, effect, "
        "or unavailable reason in default advice unless the user explicitly asks. "
        "Light Ball species-stat item context may appear only as limited "
        "species_stat_item_context. species_stat_item_context applies only "
        "when Light Ball is user-confirmed, Champions legal, holder species "
        "is Pikachu, and local species-stat metadata exists. It is a sibling "
        "explanation of an applied Light Ball modifier in "
        "damage_estimate.item_effects. Eligible Pikachu Light Ball damage "
        "estimates use default stat assumptions plus the supported Light Ball "
        "species-stat modifier, and raw damage rolls plus ko_context are based "
        "on those adjusted estimate rolls. "
        "damage_estimate.item_effects remains the source of truth for whether "
        "a supported item modifier was applied to a specific estimate. When "
        "species_stat_item_context is available, say Light Ball is a "
        "Pikachu-specific offensive item context applied in the damage estimate "
        "when damage_estimate.item_effects marks the supported modifier as "
        "applied. "
        "Do not say Light Ball is not included or Light Ball is not modeled "
        "when species_stat_item_context is available. Say this is not final "
        "stat truth and not a final KO guarantee. Do not generalize Light "
        "Ball to non-Pikachu holders. Do not say guaranteed KO, always doubles "
        "damage, confirmed OHKO because of Light Ball, all Electric-type "
        "Pokemon benefit from Light Ball, Light Ball works on any holder, "
        "final stats are fully known, or exact EV/IV/nature-adjusted stats "
        "are known. If species_stat_item_context is unavailable, treat the "
        "reason as developer/debug/contract metadata only and do not mention "
        "Light Ball, non-Pikachu mismatch, unsupported reason, missing "
        "metadata, or not modeled wording in default advice unless the user "
        "explicitly asks. "
        "Damage-supported non-legal/debug items are not normal legal selector "
        "options. If a user-confirmed item is blocked by legal item coverage "
        "or marked future-only, treat the block reason as developer/debug/"
        "contract metadata and do not include that item effect in normal "
        "user-facing recommendation text. In default advice, do not mention "
        "the blocked item name, do not say user-confirmed Loaded Dice, do not "
        "say Power Herb, do not say the item is not modeled, and do not say "
        "the item effect is not included. Do not use generic substitutes such "
        "as the user-confirmed item effect, held item effect, selected item "
        "effect, or item-based limitation for blocked or future-only items. "
        "Do not mention that a blocked item exists by saying its effect is "
        "absent, ignored, unavailable, excluded, unsupported, or outside the "
        "estimate. Do not say Loaded Dice is not "
        "modeled or Power Herb is not modeled unless the user explicitly asks "
        "about that item. If the user explicitly asks about a blocked item, "
        "explain only that Champions legal coverage is not confirmed, so the "
        "item effect is not reflected in advice. Do not imply blocked or "
        "future-only items are available in Champions. For unavailable, "
        "deferred, blocked, unconfirmed, non-triggered, or absent item "
        "contexts, treat the reason as developer/debug/contract metadata by "
        "default. Do not say item effect is not included, opponent's item "
        "effect is not included, user-confirmed item effect is not included, "
        "item is not modeled, item effect is not applied, not included in "
        "this estimate, or not reflected in the calculation in default "
        "advice. Do not mention unavailable or deferred item names or effects "
        "unless the user explicitly asks about that item. If an "
        "attacker item effect is applied, mention the supported item damage "
        "modifier and do not describe the estimate as only default "
        "assumptions; describe it as default assumptions plus the supported "
        "item modifier. If Life Orb is applied, say recoil is not modeled. If "
        "Choice Scarf, Choice Band, or Choice Specs is applied, say choice lock is not modeled. "
        "Do not mention choice lock for non-Choice items such as Charcoal, "
        "Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, "
        "Leftovers, Focus Sash, or Focus Band. Life Orb recoil is not connected. "
        "Sitrus Berry and Leftovers recovery may appear only as limited "
        "recovery_context; it does not change raw damage_range or rolls. "
        "ko_context is unchanged by recovery_context, and KO/OHKO/2HKO "
        "estimates do not include recovery. recovery_context applies only "
        "when Sitrus Berry or "
        "Leftovers is user-confirmed and defender max HP is available. Sitrus "
        "Berry recovery_context is threshold recovery limited context; exact "
        "activation timing and item consumption are not tracked. Leftovers "
        "recovery_context is end-of-turn limited context; exact turn "
        "sequencing is not modeled. When recovery_context is available, keep "
        "recovery wording concise and say exact activation timing, item "
        "consumption, and turn sequencing are not modeled. Say recovery may "
        "affect follow-up KO/2HKO only under limited assumptions; do not claim "
        "final 2HKO or 3HKO truth without Turn Engine, and do not infer "
        "recovery if the item is unknown or unconfirmed. Do not say Sitrus "
        "Berry definitely activates, KO chance includes recovery, or recovery "
        "changes the damage range. Do not combine Focus Sash and recovery into final "
        "outcome claims. Bright Powder accuracy may appear only as limited "
        "accuracy_context. accuracy_context does not change raw damage_range "
        "or rolls, and ko_context is unchanged by accuracy_context. "
        "KO/OHKO/2HKO estimates do not include hit chance. Bright Powder may "
        "reduce hit reliability, but it is not damage reduction. "
        "accuracy_context applies only when Bright Powder is user-confirmed "
        "and move accuracy metadata is available. When accuracy_context is "
        "available, keep accuracy wording concise and mention that raw damage "
        "and KO/OHKO/2HKO estimates do not include hit chance. Include one "
        "concise limitation sentence that final hit probability, "
        "accuracy/evasion stages, ability/weather interactions, multi-hit "
        "accuracy, and turn sequencing are not modeled. Hit-adjusted KO "
        "probability is not calculated. Final hit probability is not "
        "calculated. Do not claim the move will miss or that a miss is "
        "guaranteed, and do not say the hit-adjusted KO chance is a percent "
        "unless an explicit future field calculates it. Do not infer Bright "
        "Powder if the item is unknown or unconfirmed. Scope Lens critical-hit "
        "context may appear only as limited critical_context. critical_context "
        "does not change raw damage_range or rolls, and ko_context is "
        "unchanged by critical_context. KO/OHKO/2HKO estimates do not include "
        "crit chance. Scope Lens may increase critical-hit likelihood, but it "
        "is not a direct damage boost. critical_context applies only when "
        "Scope Lens is user-confirmed. When critical_context is available, "
        "keep critical-hit wording concise and mention that raw damage and "
        "KO/OHKO/2HKO estimates do not include crit chance. Final "
        "critical-hit probability is not calculated. Crit-adjusted KO "
        "probability is not calculated. Do not claim the move will crit or "
        "that a critical hit is guaranteed. Do not infer Scope Lens if "
        "the item is unknown or unconfirmed. Critical-hit stages, abilities, "
        "move-specific crit effects, and turn sequencing are not modeled. "
        "King's Rock flinch context may appear only as limited "
        "flinch_context. flinch_context does not change raw damage_range or "
        "rolls, and ko_context is unchanged by flinch_context. "
        "KO/OHKO/2HKO estimates do not include flinch chance. King's Rock "
        "may add flinch pressure, but it is not a direct damage boost. "
        "flinch_context applies only when King's Rock is user-confirmed. "
        "When flinch_context is available, say the raw damage estimate is "
        "unchanged and raw ko_context is unchanged. "
        "Do not describe King's Rock with awkward wording such as damage "
        "modifier is not included; say raw damage estimate is unchanged "
        "instead. "
        "When flinch_context is available, keep flinch wording concise and "
        "mention that raw damage and KO/OHKO/2HKO estimates do not include "
        "flinch chance. Include one concise limitation sentence that speed "
        "order, target action state, abilities, multi-hit handling, and turn "
        "sequencing are not modeled. Final flinch probability is not calculated. "
        "Flinch-adjusted turn or outcome probability is not calculated. Do "
        "not claim the target will flinch, cannot move, or that flinch is "
        "guaranteed. Do not infer King's Rock if the item is unknown or "
        "unconfirmed. Speed order, target action state, abilities, multi-hit "
        "handling, and turn sequencing are not modeled. Loaded Dice multi-hit "
        "context may appear only as limited multi_hit_context. "
        "multi_hit_context does not change raw damage_range or rolls, and "
        "ko_context is unchanged by multi_hit_context. KO/OHKO/2HKO estimates "
        "do not include multi-hit count changes. Loaded Dice may improve "
        "multi-hit reliability for eligible moves, but it is not a direct "
        "damage boost. multi_hit_context applies only when Loaded Dice is "
        "user-confirmed, Champions legal coverage is confirmed, and move "
        "multi-hit metadata is available. When "
        "multi_hit_context is available, keep multi-hit wording concise and "
        "mention that raw damage and KO/OHKO/2HKO estimates do not include "
        "multi-hit count changes. Final hit count probability is not "
        "calculated. Multi-hit-adjusted KO probability is not calculated. Do "
        "not claim a specific number of hits will occur or that 5 hits are "
        "guaranteed. Do not claim Loaded Dice breaks Focus Sash unless that "
        "interaction is explicitly modeled. Do not infer Loaded Dice if the "
        "item is unknown or unconfirmed. Focus Sash, King's Rock, accuracy, "
        "crit per-hit handling, and turn sequencing are not modeled. "
        "Type-resist berry context may appear only as limited "
        "resist_berry_context. resist_berry_context does not change raw "
        "damage_range or rolls, and ko_context is unchanged by "
        "resist_berry_context. KO/OHKO/2HKO estimates do not include berry "
        "reduction; when resist_berry_context is available, explicitly say "
        "the raw damage estimate is unchanged and raw ko_context is "
        "unchanged. "
        "If resist_berry_context is unavailable, treat the unavailable reason "
        "as developer/debug/contract metadata only and do not mention the "
        "berry name, berry effect, or unavailable reason in default advice. "
        "Do not say Yache Berry effect is not applied, do not say the berry "
        "effect is not included, and do not say the berry is not modeled in "
        "default advice unless the user explicitly asks about that berry. "
        "A standard type-resist berry may reduce a qualifying "
        "super-effective hit, but berry-adjusted damage is not calculated. "
        "Berry-adjusted KO probability is not calculated. Item consumption "
        "is not tracked. Do not say the Pokemon definitely survives. Do not "
        "infer a resist berry if the item is unknown or unconfirmed. "
        "Resist berry edge cases require explicit support before advice can "
        "use them. Chilan Berry context may appear only as limited "
        "chilan_berry_context. chilan_berry_context applies only when Chilan "
        "Berry is user-confirmed, Champions legal coverage is confirmed, "
        "local metadata marks always_resist true for Normal, incoming move "
        "type is Normal, and the move is damaging. It does not change raw "
        "damage_range or rolls, and ko_context is unchanged. KO/OHKO/2HKO "
        "estimates do not include Chilan Berry reduction. Chilan-adjusted "
        "damage and Chilan-adjusted KO probability are not calculated. Item "
        "consumption is not tracked. When chilan_berry_context is available, "
        "say Chilan Berry is a Normal-type limited context and may reduce "
        "damage from a Normal-type damaging move. Say this limited context is "
        "separate from raw damage rolls and not integrated into final KO odds; "
        "raw damage rolls and ko_context remain based on the current "
        "calculator. Do not say Chilan Berry is not included or Chilan Berry "
        "is not modeled when chilan_berry_context is available. Do not say "
        "guaranteed survival, confirmed live, will survive because of Chilan "
        "Berry, KO chance is reduced to a value, final damage is halved, raw "
        "damage rolls already include Chilan Berry, or Chilan Berry applies "
        "to all move types. If chilan_berry_context is unavailable, treat "
        "the unavailable reason as developer/debug/contract metadata only "
        "and do not mention Chilan Berry, its effect, or unavailable reason "
        "in default advice unless the user explicitly asks. "
        "Focus Sash and Focus Band survival may appear only as limited "
        "survival_context, not as damage reduction; survival_context does "
        "not change raw damage_range or rolls and ko_context is unchanged. "
        "Focus Sash survival_context applies only when Focus Sash is "
        "user-confirmed and HP is full. When Focus Sash survival_context is "
        "available, say may survive at 1 HP; do not say will survive, "
        "definitely survives, or guarantees survival. Focus Band "
        "survival_context applies only when Focus Band is user-confirmed, "
        "Champions legal, and the raw incoming hit is potentially lethal. "
        "When Focus Band survival_context is available, say may occasionally "
        "survive and survival is not guaranteed; do not say will survive, "
        "guaranteed survive, cannot be KO'd, confirmed survival, safe to "
        "take the hit, or survives this hit. Focus Band activation "
        "probability and final survival probability are not calculated, "
        "and KO/OHKO/2HKO estimates do not include Focus Band activation. "
        "When survival_context is available, include one concise limitation "
        "sentence: multi-hit moves, hazards, chip damage, item consumption, "
        "activation probability, and exact turn sequencing are not modeled. "
        "Multi-hit moves, hazards, residual damage, weather/status chip, "
        "ability interactions, and exact turn sequencing are not modeled "
        "for survival_context. Do not infer Focus Sash or Focus Band if "
        "the item is unknown or unconfirmed. When discussing type matchups, "
        "use damage_estimate.type_effectiveness if present and do not call a "
        "move super effective, resisted, or immune unless that field supports "
        "it. Do not print raw type_effectiveness labels such as super_effective "
        "or not_very_effective; convert them to natural wording: super effective, "
        "not very effective, immune/no effect, or neutral. Opponent candidate move damage is not "
        "calculated in v0.18. Use my_available_moves damage_estimates to "
        "compare the user's own move options. If opponent_assumptions is "
        "present, treat possible_samples only as context-only risk profiles, "
        "not confirmed opponent sets. Do not describe sample_assumed data as "
        "user-confirmed information. Opponent assumptions version fields are "
        "developer/contract metadata; do not mention schema_version, "
        "metadata_version, or payload_features in user-facing battle advice. "
        "If calculation_usage is context_only, do "
        "not say those samples changed damage_estimate or speed_context. Do "
        "not interpret null prior_probability as zero probability, and do not "
        "claim Top-K omitted archetypes are impossible. Do not infer final "
        "turn order, KO, survival, or exact stats from possible samples. When "
        "opponent_assumptions.available is true and possible_samples exist, "
        "include at most one short limitation sentence that possible sample "
        "context exists, for example: possible opponent samples exist, but "
        "they are context only and not confirmed. Do not dump sample_id, full "
        "stats, source metadata, update_policy, coverage_probability, or full "
        "Top-K sample lists into the response. If opponent_assumptions is "
        "unavailable, do not invent samples or force a sample limitation. "
        "Opponent sample role, archetype_id, and possible_items are context-only "
        "metadata, not confirmed opponent information. Possible_items are "
        "possible assumptions, not confirmed held items. Do not enumerate "
        "opponent sample metadata by default; keep sample visibility concise.\n\n"
        f"{json.dumps(advice_payload, ensure_ascii=False, indent=2)}"
    )


def _selected_move_payload_from_advice_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    moves = payload.get("moves")
    if not isinstance(moves, dict):
        return None
    selected_move = moves.get("my_selected_move")
    if not isinstance(selected_move, dict):
        return None
    return selected_move


def normalize_observed_previous_damage_confirmation(value: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one explicit user-confirmed prior direct-damage snapshot."""
    required = {"damage", "damage_category", "damage_kind", "source_side", "target_side"}
    if set(value) != required:
        raise ValueError("observed previous damage fields are invalid")
    damage = value.get("damage")
    if isinstance(damage, bool) or not isinstance(damage, int) or damage <= 0:
        raise ValueError("observed previous damage must be positive integer")
    if value.get("damage_category") not in {"physical", "special"} or value.get("damage_kind") != "direct_move_damage" or value.get("source_side") != "opponent" or value.get("target_side") != "self":
        raise ValueError("observed previous damage context is invalid")
    return {**dict(value), "source": "user_confirmed_previous_damage", "confidence": "known"}


def _add_observed_previous_damage_context_to_advice_payload(
    payload: dict[str, Any], *, enable_observed_previous_damage_context: bool
) -> None:
    """Attach one validated user-confirmed direct-damage snapshot, if enabled."""
    raw = payload.pop("observed_previous_damage_confirmation", None)
    if not enable_observed_previous_damage_context or not isinstance(raw, Mapping):
        return
    try:
        payload["observed_previous_damage_context"] = normalize_observed_previous_damage_confirmation(raw)
    except ValueError:
        return


def _selected_opponent_move_payload_from_advice_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    moves = payload.get("moves")
    if not isinstance(moves, dict):
        return None
    selected_move = moves.get("opponent_selected_move")
    return selected_move if isinstance(selected_move, dict) else None


def _build_optional_turn_order_context_for_advice_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    own_base_speed = _active_base_speed(payload, "my_active")
    opponent_base_speed = _active_base_speed(payload, "opponent_active")
    own_final_speed = _confirmed_final_speed(payload, "my_active")
    opponent_final_speed = _confirmed_final_speed(payload, "opponent_active")
    candidate_modifiers = _turn_order_candidate_modifiers(payload)

    has_speed_source = (own_base_speed is not None and opponent_base_speed is not None) or (
        own_final_speed is not None and opponent_final_speed is not None
    )
    if not has_speed_source and not candidate_modifiers:
        return None

    return build_deterministic_turn_order_context(
        own_move_priority=None,
        opponent_move_priority=None,
        own_base_speed=own_base_speed,
        opponent_base_speed=opponent_base_speed,
        own_confirmed_final_speed=own_final_speed,
        opponent_confirmed_final_speed=opponent_final_speed,
        candidate_modifiers=candidate_modifiers,
    )


def _build_optional_opponent_move_context_for_advice_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    opponent_moves = payload.get("opponent_moves")
    if not isinstance(opponent_moves, dict):
        return None

    candidate_moves: list[dict[str, Any]] = []
    for move in _mapping_list(opponent_moves.get("known_moves")):
        visible_move = _opponent_context_move_from_payload(move, source="visible_ui")
        if visible_move is not None:
            candidate_moves.append(visible_move)
    for move in _mapping_list(opponent_moves.get("candidate_moves")):
        source = move.get("source")
        candidate_source = source if source in OPPONENT_MOVE_CONTEXT_CANDIDATE_SOURCES else "visible_or_cache_candidate"
        candidate_move = _opponent_context_move_from_payload(move, source=str(candidate_source))
        if candidate_move is not None:
            candidate_moves.append(candidate_move)

    if not candidate_moves:
        return None

    return build_opponent_move_context(
        candidate_moves=candidate_moves,
        selected_opponent_move={"status": "unknown"},
    )


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _opponent_context_move_from_payload(move: dict[str, Any], *, source: str) -> dict[str, Any] | None:
    move_id = move.get("move_id")
    if not isinstance(move_id, str) or not move_id:
        return None

    normalized: dict[str, Any] = {
        "move_id": move_id,
        "source": source,
    }
    name = move.get("name") or move.get("name_en") or move.get("name_ko")
    if isinstance(name, str) and name:
        normalized["name"] = name
    for key in ("type", "category", "power", "accuracy", "priority", "target", "effect_flags"):
        value = move.get(key)
        if value is not None:
            normalized[key] = value
    return normalized


def _active_base_speed(payload: dict[str, Any], side: str) -> int | None:
    pokemon = payload.get("pokemon")
    if not isinstance(pokemon, dict):
        return None
    active = pokemon.get(side)
    if not isinstance(active, dict):
        return None
    base_stats = active.get("base_stats")
    if not isinstance(base_stats, dict):
        return None
    speed = base_stats.get("speed")
    return speed if isinstance(speed, int) else None


def _confirmed_final_speed(payload: dict[str, Any], side: str) -> int | None:
    stat_profiles = payload.get("stat_profiles")
    if not isinstance(stat_profiles, dict):
        return None
    profile = stat_profiles.get(side)
    if not isinstance(profile, dict) or profile.get("status") != "user_confirmed_final_stats":
        return None
    final_stats = profile.get("final_stats")
    if not isinstance(final_stats, dict):
        return None
    speed = final_stats.get("spe")
    return speed if isinstance(speed, int) else None


def _turn_order_candidate_modifiers(payload: dict[str, Any]) -> list[dict[str, str]]:
    selected_move = _selected_move_payload_from_advice_payload(payload)
    if selected_move is None:
        return []
    speed_order_context = selected_move.get("speed_order_context")
    if not isinstance(speed_order_context, dict) or speed_order_context.get("available") is not True:
        return []
    item = speed_order_context.get("item")
    item_id = item.get("item_id") if isinstance(item, dict) else None
    if item_id != "quick-claw":
        return []
    return [
        {
            "source": "Quick Claw",
            "effect": "may alter move order",
        }
    ]


def _string_field(payload: dict[str, Any] | None, key: str) -> str | None:
    if payload is None:
        return None
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _move_payload_ref(payload: dict[str, Any] | None, key: str) -> str | None:
    if payload is None or key not in payload:
        return None
    return f"moves.my_selected_move.{key}"


def _add_turn_snapshot_to_advice_payload(
    payload: dict[str, Any],
    turn_snapshot: TurnSnapshot | dict[str, Any] | None,
) -> None:
    if turn_snapshot is None:
        return

    normalized_snapshot = normalize_turn_snapshot(turn_snapshot)
    payload["turn_snapshot"] = normalized_snapshot.to_dict()

    scenario = payload.setdefault("scenario", {})
    limitations = list(scenario.get("known_limitations") or ())
    for limitation in TURN_SNAPSHOT_KNOWN_LIMITATIONS:
        if limitation not in limitations:
            limitations.append(limitation)
    scenario["known_limitations"] = limitations


def _add_turn_pipeline_to_advice_payload(
    payload: dict[str, Any],
    turn_pipeline: TurnPipelineResult | dict[str, Any] | None,
) -> None:
    if turn_pipeline is None:
        return

    normalized_pipeline = normalize_turn_pipeline_result(turn_pipeline)
    if normalized_pipeline.simulated == "full":
        raise ValueError("turn_pipeline simulated='full' is not allowed in advice payload")
    if not normalized_pipeline.limitations:
        raise ValueError("turn_pipeline limitations are required")

    for event in normalized_pipeline.events:
        _validate_turn_pipeline_event_wording(event.to_dict())

    payload["turn_pipeline"] = normalized_pipeline.to_dict()

    scenario = payload.setdefault("scenario", {})
    limitations = list(scenario.get("known_limitations") or ())
    for limitation in TURN_PIPELINE_KNOWN_LIMITATIONS:
        if limitation not in limitations:
            limitations.append(limitation)
    scenario["known_limitations"] = limitations


def _add_turn_order_context_to_advice_payload(
    payload: dict[str, Any],
    turn_order_context: dict[str, Any] | None,
    *,
    enable_turn_order_context: bool,
) -> None:
    if not enable_turn_order_context:
        return
    if turn_order_context is None:
        return

    context = deepcopy(turn_order_context)
    _validate_turn_order_context_payload(context)
    payload["turn_order_context"] = context


def _add_opponent_move_context_to_advice_payload(
    payload: dict[str, Any],
    opponent_move_context: dict[str, Any] | None,
    *,
    enable_opponent_move_context: bool,
) -> None:
    if not enable_opponent_move_context:
        return
    if opponent_move_context is None:
        return

    context = deepcopy(opponent_move_context)
    _validate_opponent_move_context_payload(context)
    if _is_empty_opponent_move_context(context):
        return
    payload["opponent_move_context"] = context


def _add_battle_state_context_to_advice_payload(
    payload: dict[str, Any],
    battle_state_context: dict[str, Any] | None,
    *,
    enable_battle_state_context: bool,
) -> None:
    if not enable_battle_state_context:
        return
    if battle_state_context is None:
        return
    if not battle_state_context:
        return

    context = deepcopy(battle_state_context)
    _validate_battle_state_context_payload(context)
    if _is_empty_battle_state_context(context):
        return
    payload["battle_state_context"] = context


def _add_item_event_context_to_advice_payload(
    payload: dict[str, Any],
    item_event_context: dict[str, Any] | None,
    *,
    enable_item_event_context: bool,
) -> None:
    if not enable_item_event_context or item_event_context is None:
        return

    context = deepcopy(item_event_context)
    if not isinstance(context, dict) or set(context) != {"observed_events"}:
        raise ValueError("item_event_context must contain observed_events only")
    observed_events = context.get("observed_events")
    if not isinstance(observed_events, list):
        raise ValueError("item_event_context observed_events must be a list")

    normalized_events: list[dict[str, Any]] = []
    for event in observed_events:
        if not isinstance(event, dict):
            raise ValueError("item_event_context observed_events must contain mappings")
        confidence = event.get("confidence")
        candidate = {key: value for key, value in event.items() if key != "confidence"}
        normalized = validate_explicit_user_item_event_confirmation(candidate)
        if confidence != "observed":
            raise ValueError("item_event_context observed event confidence must be observed")
        normalized_events.append({**normalized, "confidence": "observed"})

    if normalized_events:
        payload["item_event_context"] = {"observed_events": normalized_events}


def _add_condition_context_to_advice_payload(
    payload: dict[str, Any],
    condition_context: dict[str, Any] | None,
    *,
    enable_condition_context: bool,
) -> None:
    """Add only validated user-confirmed current conditions to advice payload."""
    if not enable_condition_context or condition_context is None:
        return

    context = deepcopy(condition_context)
    if not isinstance(context, dict) or set(context) != {"current_conditions"}:
        raise ValueError("condition_context must contain current_conditions only")
    current_conditions = context.get("current_conditions")
    if not isinstance(current_conditions, list):
        raise ValueError("condition_context current_conditions must be a list")

    by_side: dict[str, dict[str, Any]] = {}
    for condition in current_conditions:
        if not isinstance(condition, dict):
            raise ValueError("condition_context current_conditions must contain mappings")
        confidence = condition.get("confidence")
        candidate = {key: value for key, value in condition.items() if key != "confidence"}
        normalized = normalize_user_confirmed_current_condition(candidate)
        if confidence != "known":
            raise ValueError("condition_context current condition confidence must be known")
        by_side[normalized["side"]] = {**normalized, "confidence": "known"}

    normalized_conditions = [by_side[side] for side in ("self", "opponent") if side in by_side]
    if normalized_conditions:
        payload["condition_context"] = {"current_conditions": normalized_conditions}


def _add_ability_context_to_advice_payload(
    payload: dict[str, Any],
    ability_context: dict[str, Any] | None,
    *,
    enable_ability_context: bool,
) -> None:
    """Add validated current ability identities without adding prompt behavior."""
    if not enable_ability_context or ability_context is None:
        return

    context = deepcopy(ability_context)
    if not isinstance(context, dict) or set(context) != {"current_abilities"}:
        raise ValueError("ability_context must contain current_abilities only")
    current_abilities = context.get("current_abilities")
    if not isinstance(current_abilities, list):
        raise ValueError("ability_context current_abilities must be a list")

    by_side: dict[str, dict[str, Any]] = {}
    for ability in current_abilities:
        if not isinstance(ability, dict):
            raise ValueError("ability_context current_abilities must contain mappings")
        confidence = ability.get("confidence")
        candidate = {key: value for key, value in ability.items() if key != "confidence"}
        normalized = normalize_user_confirmed_current_ability(candidate)
        if confidence != "known":
            raise ValueError("ability_context current ability confidence must be known")
        by_side[normalized["side"]] = {**normalized, "confidence": "known"}

    normalized_abilities = [by_side[side] for side in ("self", "opponent") if side in by_side]
    if normalized_abilities:
        payload["ability_context"] = {"current_abilities": normalized_abilities}


def _add_stat_stage_context_to_advice_payload(
    payload: dict[str, Any],
    stat_stage_context: dict[str, Any] | None,
    *,
    enable_stat_stage_context: bool,
) -> None:
    if not enable_stat_stage_context or stat_stage_context is None:
        return
    context = deepcopy(stat_stage_context)
    if not isinstance(context, dict) or set(context) != {"current_stages"}:
        raise ValueError("stat_stage_context must contain current_stages only")
    stages = context.get("current_stages")
    if not isinstance(stages, list):
        raise ValueError("stat_stage_context current_stages must be a list")
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for stage in stages:
        if not isinstance(stage, dict):
            raise ValueError("stat_stage_context current_stages must contain mappings")
        confidence = stage.get("confidence")
        normalized = normalize_user_confirmed_current_stat_stage({key: value for key, value in stage.items() if key != "confidence"})
        if confidence != "known":
            raise ValueError("stat_stage_context current stage confidence must be known")
        by_key[(normalized["side"], normalized["stat"])] = {**normalized, "confidence": "known"}
    normalized_stages = [by_key[key] for key in sorted(by_key, key=lambda key: (("self", "opponent").index(key[0]), key[1]))]
    if normalized_stages:
        payload["stat_stage_context"] = {"current_stages": normalized_stages}


def _add_field_state_context_to_advice_payload(
    payload: dict[str, Any],
    field_state_context: dict[str, Any] | None,
    *,
    enable_field_state_context: bool,
) -> None:
    if not enable_field_state_context or field_state_context is None:
        return
    context = deepcopy(field_state_context)
    if not isinstance(context, dict) or set(context) != {"current_field"}:
        raise ValueError("field_state_context must contain current_field only")
    current_field = context.get("current_field")
    if not isinstance(current_field, dict):
        raise ValueError("field_state_context current_field must be a mapping")
    confidence = current_field.get("confidence")
    normalized = normalize_user_confirmed_current_field_state(
        {key: value for key, value in current_field.items() if key != "confidence"}
    )
    if confidence != "known":
        raise ValueError("field_state_context confidence must be known")
    payload["field_state_context"] = {"current_field": {**normalized, "confidence": "known"}}


def _add_battle_format_context_to_advice_payload(
    payload: dict[str, Any], context: dict[str, Any] | None, *, enable_battle_format_context: bool
) -> None:
    """Attach only the explicit, user-confirmed battle format."""
    if not enable_battle_format_context or context is None:
        return
    if not isinstance(context, dict) or set(context) != {"current_battle_format"}:
        raise ValueError("battle_format_context must contain current_battle_format only")
    current = context.get("current_battle_format")
    if not isinstance(current, dict) or current.get("confidence") != "known":
        raise ValueError("battle_format_context must be known")
    normalized = normalize_user_confirmed_battle_format({key: value for key, value in current.items() if key != "confidence"})
    payload["battle_format_context"] = {"current_battle_format": {**normalized, "confidence": "known"}}


def _add_final_stat_context_to_advice_payload(payload: dict[str, Any], context: dict[str, Any] | None, *, enable_final_stat_context: bool) -> None:
    if not enable_final_stat_context or context is None:
        return
    if not isinstance(context, dict) or set(context) != {"current_final_stats"} or not isinstance(context["current_final_stats"], list):
        raise ValueError("final_stat_context must contain current_final_stats only")
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in context["current_final_stats"]:
        if not isinstance(entry, dict) or entry.get("confidence") != "known":
            raise ValueError("final_stat_context entry must be known")
        normalized = normalize_user_confirmed_final_battle_stat({key: value for key, value in entry.items() if key != "confidence"})
        by_key[(normalized["side"], normalized["stat"])] = {**normalized, "confidence": "known"}
    if by_key:
        payload["final_stat_context"] = {"current_final_stats": [by_key[key] for key in sorted(by_key)]}


def _add_deterministic_calculation_context_to_advice_payload(
    payload: dict[str, Any], context: dict[str, Any] | None, *, enable_deterministic_calculation_context: bool
) -> None:
    """Attach only internally constructed stage-only calculation results."""
    if not enable_deterministic_calculation_context or context is None:
        return
    expected = build_deterministic_calculation_context(
        payload.get("final_stat_context"),
        payload.get("stat_stage_context"),
        _selected_move_payload_from_advice_payload(payload),
        payload.get("current_hp_context"),
        payload.get("pokemon"),
        payload.get("condition_context"),
        payload.get("field_state_context"),
        payload.get("battle_format_context"),
        _selected_opponent_move_payload_from_advice_payload(payload),
        observed_previous_damage_context=payload.get("observed_previous_damage_context"),
        battle_counter_context=payload.get("battle_counter_confirmation"),
        consecutive_use_context=payload.get("consecutive_use_confirmation"),
    )
    if expected is None or context != expected:
        raise ValueError("deterministic_calculation_context must match trusted stage-only inputs")
    payload["deterministic_calculation_context"] = deepcopy(expected)


def _add_current_hp_context_to_advice_payload(payload: dict[str, Any], context: dict[str, Any] | None, *, enable_current_hp_context: bool) -> None:
    if not enable_current_hp_context or context is None:
        return
    if not isinstance(context, dict) or not isinstance(context.get("current_hp"), list):
        raise ValueError("current_hp_context must contain current_hp")
    entries = [normalize_user_confirmed_current_hp(entry) for entry in context["current_hp"] if isinstance(entry, dict)]
    if entries:
        payload["current_hp_context"] = {"current_hp": entries}


def _validate_battle_state_context_payload(context: dict[str, Any]) -> None:
    if not isinstance(context, dict):
        raise ValueError("battle_state_context must be a mapping")
    if context.get("kind") != "battle_state_context":
        raise ValueError("battle_state_context kind must be battle_state_context")
    if context.get("confidence") not in {"limited", "unknown"}:
        raise ValueError("battle_state_context confidence is not allowed")
    if set(context) != {
        "kind",
        "confidence",
        "self_active",
        "opponent_active",
        "field",
        "known_conditions",
        "unsupported",
        "safety_notes",
    }:
        raise ValueError("battle_state_context top-level shape is not allowed")

    _validate_battle_state_active_side(context.get("self_active"), "self_active")
    _validate_battle_state_active_side(context.get("opponent_active"), "opponent_active")
    _validate_battle_state_field(context.get("field"))

    known_conditions = context.get("known_conditions")
    if not isinstance(known_conditions, list):
        raise ValueError("battle_state_context known_conditions must be a list")
    for condition in known_conditions:
        if not isinstance(condition, dict):
            raise ValueError("battle_state_context known_conditions must contain mappings")

    unsupported = context.get("unsupported")
    required_unsupported = set(BATTLE_STATE_CONTEXT_UNSUPPORTED_BOUNDARIES)
    if not isinstance(unsupported, list) or not required_unsupported.issubset(set(unsupported)):
        raise ValueError("battle_state_context unsupported boundaries are required")

    safety_notes = context.get("safety_notes")
    required_safety_notes = set(BATTLE_STATE_CONTEXT_SAFETY_NOTES)
    if not isinstance(safety_notes, list) or not required_safety_notes.issubset(set(safety_notes)):
        raise ValueError("battle_state_context safety notes are required")

    _validate_battle_state_context_sources(context)
    _validate_no_battle_state_context_forbidden_fields(context)


def _validate_battle_state_active_side(active_side: Any, side_name: str) -> None:
    if not isinstance(active_side, dict):
        raise ValueError(f"battle_state_context {side_name} must be a mapping")
    if set(active_side) != set(BATTLE_STATE_CONTEXT_ACTIVE_FIELDS):
        raise ValueError(f"battle_state_context {side_name} shape is not allowed")

    _validate_battle_state_name_or_unknown(active_side["species"], f"{side_name}.species")
    _validate_battle_state_value_or_unknown(active_side["current_hp_percent"], f"{side_name}.current_hp_percent")
    for field_name in ("status", "boosts"):
        _validate_battle_state_known_value_or_unknown(active_side[field_name], f"{side_name}.{field_name}")
    _validate_battle_state_item_or_unknown(active_side["item"], f"{side_name}.item")


def _validate_battle_state_field(field: Any) -> None:
    if not isinstance(field, dict):
        raise ValueError("battle_state_context field must be a mapping")
    if set(field) != set(BATTLE_STATE_CONTEXT_FIELD_FIELDS):
        raise ValueError("battle_state_context field shape is not allowed")
    for field_name in BATTLE_STATE_CONTEXT_FIELD_FIELDS:
        _validate_battle_state_known_field_value_or_unknown(field[field_name], f"field.{field_name}")


def _validate_battle_state_name_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("source") not in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    if not value.get("name"):
        raise ValueError(f"battle_state_context {field_name} requires name")


def _validate_battle_state_value_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("source") not in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    known_value = value.get("value")
    if known_value is None or known_value == "unknown":
        raise ValueError(f"battle_state_context {field_name} requires known value")


def _validate_battle_state_known_value_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("known") is not True:
        raise ValueError(f"battle_state_context {field_name} known value is not allowed")
    if value.get("source") not in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    known_value = value.get("value")
    if known_value is None or known_value == "unknown":
        raise ValueError(f"battle_state_context {field_name} requires known value")


def _validate_battle_state_item_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("known") is not True:
        raise ValueError(f"battle_state_context {field_name} known value is not allowed")
    if value.get("source") not in BATTLE_STATE_CONTEXT_ITEM_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    known_value = value.get("value")
    if known_value is None or known_value == "unknown":
        raise ValueError(f"battle_state_context {field_name} requires known value")


def _validate_battle_state_known_field_value_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("known") is not True:
        raise ValueError(f"battle_state_context {field_name} known value is not allowed")
    if value.get("source") not in BATTLE_STATE_CONTEXT_FIELD_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    known_value = value.get("value")
    if known_value is None or known_value == "unknown":
        raise ValueError(f"battle_state_context {field_name} requires known value")
    field_key = field_name.rsplit(".", maxsplit=1)[-1]
    if not _battle_state_field_value_is_allowed(field_key, known_value):
        raise ValueError(f"battle_state_context {field_name} known value is not allowed")


def _battle_state_field_value_is_allowed(field_name: str, value: Any) -> bool:
    if field_name in {"screens", "hazards"}:
        return _battle_state_side_specific_field_value_is_allowed(value)
    if field_name in {"weather", "terrain"}:
        return isinstance(value, str) and bool(value.strip())
    if field_name == "room":
        return _battle_state_simple_field_value_is_allowed(value)
    return False


def _battle_state_simple_field_value_is_allowed(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value) and all(isinstance(key, str) and key.strip() for key in value)
    return False


def _battle_state_side_specific_field_value_is_allowed(value: Any) -> bool:
    if not isinstance(value, dict) or not value:
        return False
    if not set(value).issubset({"self", "opponent"}):
        return False
    if not all(_battle_state_side_condition_list_is_allowed(side_value) for side_value in value.values()):
        return False
    if any(_battle_state_side_condition_list_has_known_value(side_value) for side_value in value.values()):
        return True
    return set(value) == {"self", "opponent"} and all(isinstance(side_value, list) for side_value in value.values())


def _battle_state_side_condition_list_is_allowed(value: Any) -> bool:
    if value == "unknown":
        return True
    if isinstance(value, list):
        return all(isinstance(entry, str) and bool(entry.strip()) for entry in value)
    return False


def _battle_state_side_condition_list_has_known_value(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _validate_battle_state_context_sources(value: Any) -> None:
    if isinstance(value, dict):
        source = value.get("source")
        if source is not None:
            if source in BATTLE_STATE_CONTEXT_FORBIDDEN_SOURCES:
                raise ValueError("battle_state_context source is forbidden")
            if source not in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
                raise ValueError("battle_state_context source is not allowed")
        for child_value in value.values():
            _validate_battle_state_context_sources(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _validate_battle_state_context_sources(child_value)


def _validate_no_battle_state_context_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in BATTLE_STATE_CONTEXT_FORBIDDEN_FIELDS:
                raise ValueError(f"battle_state_context must not include {key!r}")
            _validate_no_battle_state_context_forbidden_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _validate_no_battle_state_context_forbidden_fields(child_value)


def _is_empty_battle_state_context(context: dict[str, Any]) -> bool:
    return not _battle_state_context_has_known_source(context)


def _battle_state_context_has_known_source(value: Any) -> bool:
    if isinstance(value, dict):
        source = value.get("source")
        if source in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
            return True
        return any(_battle_state_context_has_known_source(child_value) for child_value in value.values())
    if isinstance(value, list):
        return any(_battle_state_context_has_known_source(child_value) for child_value in value)
    return False


def _validate_opponent_move_context_payload(context: dict[str, Any]) -> None:
    if context.get("kind") != "opponent_move_context":
        raise ValueError("opponent_move_context kind must be opponent_move_context")
    if context.get("confidence") not in {"limited", "unknown"}:
        raise ValueError("opponent_move_context confidence is not allowed")

    selected = context.get("selected_opponent_move")
    if not isinstance(selected, dict):
        raise ValueError("opponent_move_context selected_opponent_move must be a mapping")
    if selected.get("status") not in {"unknown", "explicit"}:
        raise ValueError("opponent_move_context selected_opponent_move status is not allowed")
    if selected.get("status") == "explicit":
        if selected.get("source") not in OPPONENT_MOVE_CONTEXT_TRUSTED_KNOWN_SOURCES:
            raise ValueError("opponent_move_context explicit selected move requires trusted source")
        if not selected.get("move_id") or not selected.get("name"):
            raise ValueError("opponent_move_context explicit selected move requires move_id and name")

    known_moves = context.get("known_opponent_moves")
    if not isinstance(known_moves, list):
        raise ValueError("opponent_move_context known_opponent_moves must be a list")
    for move in known_moves:
        if not isinstance(move, dict):
            raise ValueError("opponent_move_context known moves must be mappings")
        _validate_opponent_move_metadata_fields(move)
        if move.get("source") not in OPPONENT_MOVE_CONTEXT_TRUSTED_KNOWN_SOURCES:
            raise ValueError("opponent_move_context known move source is not trusted")
        if move.get("confirmed") is not True:
            raise ValueError("opponent_move_context known moves must be confirmed")

    candidate_moves = context.get("candidate_moves")
    if not isinstance(candidate_moves, list):
        raise ValueError("opponent_move_context candidate_moves must be a list")
    for move in candidate_moves:
        _validate_opponent_move_candidate(move)

    priority_candidates = context.get("priority_move_candidates")
    if not isinstance(priority_candidates, list):
        raise ValueError("opponent_move_context priority_move_candidates must be a list")
    for move in priority_candidates:
        _validate_opponent_move_candidate(move)

    unsupported = context.get("unsupported")
    required_unsupported = set(OPPONENT_MOVE_CONTEXT_UNSUPPORTED_BOUNDARIES)
    if not isinstance(unsupported, list) or not required_unsupported.issubset(set(unsupported)):
        raise ValueError("opponent_move_context unsupported boundaries are required")

    safety_notes = context.get("safety_notes")
    if not isinstance(safety_notes, list) or "Candidate moves are not confirmed selected moves." not in safety_notes:
        raise ValueError("opponent_move_context candidate safety note is required")

    _validate_no_opponent_move_context_forbidden_fields(context)


def _validate_opponent_move_candidate(move: Any) -> None:
    if not isinstance(move, dict):
        raise ValueError("opponent_move_context candidate moves must be mappings")
    _validate_opponent_move_metadata_fields(move)
    if move.get("source") not in OPPONENT_MOVE_CONTEXT_CANDIDATE_SOURCES:
        raise ValueError("opponent_move_context candidate source is not allowed")
    if move.get("confirmed") is not False:
        raise ValueError("opponent_move_context candidate moves must be unconfirmed")
    if move.get("selected") is not False:
        raise ValueError("opponent_move_context candidate moves must be unselected")


def _validate_opponent_move_metadata_fields(move: dict[str, Any]) -> None:
    if not set(move).issubset(OPPONENT_MOVE_CONTEXT_ALLOWED_MOVE_FIELDS):
        raise ValueError("opponent_move_context move metadata field is not allowed")


def _validate_no_opponent_move_context_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in OPPONENT_MOVE_CONTEXT_FORBIDDEN_FIELDS:
                raise ValueError(f"opponent_move_context must not include {key!r}")
            _validate_no_opponent_move_context_forbidden_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _validate_no_opponent_move_context_forbidden_fields(child_value)


def _is_empty_opponent_move_context(context: dict[str, Any]) -> bool:
    return (
        context.get("selected_opponent_move") == {"status": "unknown"}
        and not context.get("known_opponent_moves")
        and not context.get("candidate_moves")
        and not context.get("priority_move_candidates")
    )


def _validate_turn_order_context_payload(context: dict[str, Any]) -> None:
    if context.get("kind") != "deterministic_turn_order_context":
        raise ValueError("turn_order_context kind must be deterministic_turn_order_context")
    if context.get("confidence") not in TURN_ORDER_CONTEXT_CONFIDENCE_VALUES:
        raise ValueError("turn_order_context confidence is not allowed")

    priority = context.get("priority")
    if not isinstance(priority, dict):
        raise ValueError("turn_order_context priority must be a mapping")
    if priority.get("priority_relation") not in TURN_ORDER_CONTEXT_PRIORITY_RELATION_VALUES:
        raise ValueError("turn_order_context priority_relation is not allowed")

    speed = context.get("speed")
    if not isinstance(speed, dict):
        raise ValueError("turn_order_context speed must be a mapping")
    if speed.get("speed_relation") not in TURN_ORDER_CONTEXT_SPEED_RELATION_VALUES:
        raise ValueError("turn_order_context speed_relation is not allowed")

    if context.get("order_hint") not in TURN_ORDER_CONTEXT_ORDER_HINT_VALUES:
        raise ValueError("turn_order_context order_hint is not allowed")

    unsupported = context.get("unsupported")
    if not isinstance(unsupported, list) or not TURN_ORDER_CONTEXT_REQUIRED_UNSUPPORTED.issubset(set(unsupported)):
        raise ValueError("turn_order_context unsupported boundaries are required")

    modifiers = context.get("candidate_modifiers")
    if not isinstance(modifiers, list):
        raise ValueError("turn_order_context candidate_modifiers must be a list")
    for modifier in modifiers:
        if not isinstance(modifier, dict) or modifier.get("resolved") is not False:
            raise ValueError("turn_order_context candidate modifiers must be unresolved")

    _validate_no_turn_order_context_forbidden_fields(context)


def _validate_no_turn_order_context_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in TURN_ORDER_CONTEXT_FORBIDDEN_FIELDS:
                raise ValueError(f"turn_order_context must not include {key!r}")
            _validate_no_turn_order_context_forbidden_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _validate_no_turn_order_context_forbidden_fields(child_value)


def _validate_turn_pipeline_event_wording(event: dict[str, Any]) -> None:
    rendered_parts = []
    for key in ("summary", "limitations"):
        value = event.get(key)
        if isinstance(value, str):
            rendered_parts.append(value)
        elif isinstance(value, list):
            rendered_parts.extend(item for item in value if isinstance(item, str))
    rendered = " ".join(rendered_parts).lower()
    forbidden_phrases = (
        "item was consumed",
        "item has been consumed",
        "item consumption resolved",
        "exact trigger result",
        "trigger result is resolved",
        "exact post-turn hp",
        "post-turn hp is",
        "guaranteed move order",
        "speed tie resolved",
        "rng resolved",
        "full turn simulation completed",
    )
    for phrase in forbidden_phrases:
        if phrase in rendered:
            raise ValueError(f"turn_pipeline event wording must not claim {phrase!r}")


def _build_turn_snapshot_prompt_guard(payload: dict[str, Any]) -> str:
    if "turn_snapshot" not in payload:
        return ""
    return (
        "If turn_snapshot is present, treat it as selected/pre-turn known state "
        "context only, not full turn simulation. Do not claim full turn "
        "simulation, exact item trigger result, item was consumed, exact "
        "post-turn HP, guaranteed move order, or exact status resolution from "
        "turn_snapshot alone. Item trigger evaluation, item consumption, "
        "post-damage HP updates, speed/order simulation, and exact status "
        "resolution are not implemented. Use turn_snapshot only as known state "
        "context. "
    )


def _build_turn_pipeline_prompt_guard(payload: dict[str, Any]) -> str:
    if "turn_pipeline" not in payload:
        return ""
    return (
        "If turn_pipeline is present, treat it as a limited planning/debug "
        "summary only, not full turn simulation. Do not claim RNG resolution, "
        "item consumption, exact post-turn HP, guaranteed move order, exact "
        "item trigger result, speed tie resolution, or exact status resolution "
        "from turn_pipeline. Use turn_pipeline events only as candidate or "
        "known-modifier context; candidate events are not resolved outcomes. "
        "Do not treat turn_pipeline as final battle truth or as a replacement "
        "for damage_estimate, ko_context, or existing item contexts. "
    )


def _build_turn_order_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "turn_order_context" not in payload:
        return ""
    return (
        "If turn_order_context is present, treat it as limited planning context, "
        "not a resolved move order. Use it only as a cautious hint when priority "
        "and Speed data are available. Do not claim exact final move order. Do "
        "not claim speed ties are resolved. Do not claim RNG items activate. Do "
        "not infer item consumption. Do not infer post-turn HP from "
        "turn_order_context. "
    )


def _build_opponent_move_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "opponent_move_context" not in payload:
        return ""
    return (
        "If opponent_move_context is present, treat it as based only on "
        "explicitly known or visible opponent move data. Known opponent moves "
        "are not necessarily the opponent's selected move this turn unless "
        "selected_opponent_move is explicit. Candidate moves are not confirmed "
        "moves. Candidate moves are not confirmed selected moves. Do not infer "
        "hidden movesets. Do not infer opponent sets. Do not infer the "
        "opponent's selected move unless explicitly provided. Do not infer "
        "EVs, IVs, nature, hidden item, weather, terrain, boosts, RNG results, "
        "item consumption, or post-turn HP unless explicitly provided. Treat "
        "unsupported entries as boundaries, not facts to fill in. "
    )


def _build_battle_state_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "battle_state_context" not in payload:
        return ""
    return (
        "If battle_state_context is present, treat it only as a visible or "
        "explicit battle-state snapshot, not a resolved turn simulation. "
        "Unknown battle state fields must remain unknown. Do not infer hidden "
        "items. Do not infer EVs, IVs, or nature. Do not infer boosts, status, "
        "weather, terrain, hazards, screens, or room unless explicitly "
        "provided. Do not reverse-engineer hidden state from damage estimates "
        "or KO context. Do not claim post-turn HP, item consumption, RNG "
        "result, speed tie result, Quick Claw activation, or full turn outcome "
        "from battle_state_context. Treat unsupported entries as boundaries, "
        "not facts to fill in. "
    )


def _build_item_event_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "item_event_context" not in payload:
        return ""
    return (
        "If item_event_context is present, treat it only as an explicitly "
        "user-confirmed observed item event. Distinguish current known items "
        "from explicitly observed item events. Where current known item "
        "context is present, briefly acknowledge each known item by side and "
        "item as user-confirmed current context only, not an observed "
        "activation, consumption, or resolved effect. Keep those current "
        "known items separate from explicitly observed item events. Briefly "
        "acknowledge each "
        "observed event by side, item, and event type as user-confirmed "
        "observation only. It is observed context only, not "
        "a resolved mechanic result, exact calculation, post-turn state, RNG "
        "result, or resolved turn order. Do not infer exact HP, exact damage, "
        "item consumption, item effect application, Quick Claw RNG outcome, "
        "Focus Sash HP result, or Berry recovery amount from it. "
    )


def _build_condition_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "condition_context" not in payload:
        return ""
    return (
        "If condition_context is present, treat each current condition only as "
        "user-confirmed present-state context. Briefly acknowledge each current "
        "condition by side and condition type as user-confirmed present-state "
        "context. Distinguish self and opponent condition types, including none "
        "(user-confirmed no current major status) versus unknown (current major "
        "status is not known). Do "
        "not infer when a condition was applied, whether it triggered or ticked "
        "this turn, exact status damage, sleep duration, wake-up turn, freeze "
        "thaw, full paralysis, post-turn HP or condition state, RNG outcome, "
        "or final order from it. "
    )


def _build_ability_context_prompt_guard(payload: dict[str, Any]) -> str:
    """Describe known abilities without promoting them into battle outcomes."""
    if "ability_context" not in payload:
        return ""
    return (
        "If ability_context is present, treat each ability only as a "
        "user-confirmed current ability identity. Briefly acknowledge each "
        "ability by side and identity, keeping self and opponent separate; "
        "unknown means the current ability is not known. Do not infer possible "
        "species abilities, activation, trigger, suppression, replacement, "
        "copying, restoration, resolved immunity or prevention, exact stat or "
        "damage modifiers, HP, boosted stat, RNG, or final order from it. "
    )


def _build_stat_stage_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "stat_stage_context" not in payload:
        return ""
    return (
        "If stat_stage_context is present, treat each entry only as a user-confirmed "
        "current stat stage by side and stat. Do not infer when or why it changed, "
        "the move, ability, or item that caused it, exact final stats, damage, HP, "
        "or final move order. Keep every side and stat separate. "
    )


def _build_field_state_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "field_state_context" not in payload:
        return ""
    return (
        "If field_state_context is present, treat weather, terrain, global effects, and side "
        "effects only as user-confirmed current field identities. Do not infer how or when "
        "they began, remaining duration, or a source move, ability, or item. Do not turn them "
        "into exact damage, HP, effective speed, or final order. Keep global effects separate "
        "from self and opponent side effects; explicit none means confirmed current absence, not "
        "that an effect just ended. "
    )


def _build_final_stat_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "final_stat_context" not in payload:
        return ""
    return (
        "If final_stat_context is present, treat each value only as a user-confirmed, "
        "stage-unmodified final stat. Do not infer EVs, IVs, nature, level, item, or ability; "
        "do not apply stages or temporary modifiers unless a deterministic result is provided, "
        "and do not infer exact damage, KO chance, HP, or final order. "
    )


def _build_deterministic_calculation_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "deterministic_calculation_context" not in payload:
        return ""
    return (
        "deterministic_calculation_context contains deterministic stage-only effective-stat and Speed-comparison "
        "results. Do not recalculate or alter them. They are not final move order: do not apply or claim priority, "
        "item, ability, weather, terrain, Tailwind, Trick Room, or RNG modifiers. A tie means equal stage-adjusted "
        "Speed only, never a tie winner or first action. Any damage estimate is base-damage-stage-only: do not alter "
        "its range or infer STAB, type effectiveness, burn, item, ability, weather, terrain, screens, critical hits, "
        "remaining HP, or KO chance. A type-aware estimate includes only ordinary STAB and the base type chart: do not "
        "alter its values or infer ability/item type overrides (including Levitate), Adaptability, Protean, Libero, Tera, "
        "or type-changing effects. If an HP assessment is present, use only its declared current/max HP, 16-roll "
        "OHKO count, and independent two-hit roll-pair result; do not add recovery, chip, hazards, survival effects, "
        "accuracy, critical hits, or between-turn state changes. "
    )


def _build_current_hp_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "current_hp_context" not in payload:
        return ""
    return (
        "current_hp_context contains user-confirmed exact current HP and maximum HP snapshots. Do not convert visible "
        "HP percent into exact HP, infer post-turn HP, damage taken, recovery, or survival effects. "
    )


def _build_condition_item_event_attribution_prompt_guard(payload: dict[str, Any]) -> str:
    """Require compact category readback only for supplied trusted context."""
    attribution_lines: list[str] = []
    condition_context = payload.get("condition_context")
    if isinstance(condition_context, dict):
        conditions = condition_context.get("current_conditions")
        if isinstance(conditions, list):
            for condition in conditions:
                if isinstance(condition, dict):
                    side = condition.get("side")
                    condition_type = condition.get("condition_type")
                    if isinstance(side, str) and isinstance(condition_type, str):
                        attribution_lines.append(
                            f"Current condition - {side}: {condition_type} (user-confirmed current state)."
                        )

    ability_context = payload.get("ability_context")
    if isinstance(ability_context, dict):
        abilities = ability_context.get("current_abilities")
        if isinstance(abilities, list):
            for ability in abilities:
                if isinstance(ability, dict):
                    side = ability.get("side")
                    ability_name = ability.get("ability")
                    if isinstance(side, str) and isinstance(ability_name, str):
                        attribution_lines.append(
                            f"Current ability - {side}: {ability_name} (user-confirmed current identity)."
                        )

    stat_stage_context = payload.get("stat_stage_context")
    if isinstance(stat_stage_context, dict) and isinstance(stat_stage_context.get("current_stages"), list):
        for stage in stat_stage_context["current_stages"]:
            if isinstance(stage, dict) and isinstance(stage.get("side"), str) and isinstance(stage.get("stat"), str) and isinstance(stage.get("stage"), int):
                attribution_lines.append(f"Current stat stage - {stage['side']}: {stage['stat']} {stage['stage']:+d} (user-confirmed current stage).")

    field_state_context = payload.get("field_state_context")
    if isinstance(field_state_context, dict) and isinstance(field_state_context.get("current_field"), dict):
        field = field_state_context["current_field"]
        weather, terrain = field.get("weather"), field.get("terrain")
        if isinstance(weather, str):
            attribution_lines.append(f"Current weather: {weather} (user-confirmed current field state).")
        if isinstance(terrain, str):
            attribution_lines.append(f"Current terrain: {terrain} (user-confirmed current field state).")
        for effect in field.get("global_effects", []):
            if isinstance(effect, str):
                attribution_lines.append(f"Current global field effect: {effect} (user-confirmed current field state).")
        for effect in field.get("side_effects", []):
            if isinstance(effect, dict) and isinstance(effect.get("side"), str) and isinstance(effect.get("effect"), str):
                attribution_lines.append(f"Current side field effect - {effect['side']}: {effect['effect']} (user-confirmed current field state).")

    item_event_context = payload.get("item_event_context")
    if isinstance(item_event_context, dict):
        events = item_event_context.get("observed_events")
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    side = event.get("side")
                    item = event.get("item")
                    event_type = event.get("event_type")
                    if isinstance(side, str) and isinstance(item, str) and isinstance(event_type, str):
                        attribution_lines.append(
                            "Observed item event - "
                            f"{side}: {item} / {event_type} (explicitly user-confirmed observation)."
                        )

    if not attribution_lines:
        return ""
    return (
        "Trusted context attribution: "
        + " ".join(attribution_lines)
        + " Briefly acknowledge each listed category and identity while giving advice. "
        "Do not merge current conditions with observed item events. Keep current "
        "abilities, current stat stages, and current field identities separate from both categories, and do not promote any of "
        "them into a resolved effect, exact HP, damage, timing, RNG, or "
        "final-order claim. "
    )


def build_trusted_context_acknowledgement_entries(payload: dict[str, Any]) -> tuple[tuple[str, str, str, str | None], ...]:
    """Return canonical acknowledgement entries from validated normalized payload."""
    entries: list[tuple[str, str, str, str | None]] = []
    condition_context = payload.get("condition_context")
    if isinstance(condition_context, dict) and isinstance(condition_context.get("current_conditions"), list):
        for condition in condition_context["current_conditions"]:
            if isinstance(condition, dict):
                side, condition_type = condition.get("side"), condition.get("condition_type")
                if isinstance(side, str) and isinstance(condition_type, str):
                    entries.append(("current_condition", side.lower(), condition_type.lower(), None))
    ability_context = payload.get("ability_context")
    if isinstance(ability_context, dict) and isinstance(ability_context.get("current_abilities"), list):
        for ability in ability_context["current_abilities"]:
            if isinstance(ability, dict):
                side, ability_name = ability.get("side"), ability.get("ability")
                if isinstance(side, str) and isinstance(ability_name, str):
                    entries.append(("current_ability", side.lower(), _normalize_trusted_context_identity(ability_name), None))
    stat_stage_context = payload.get("stat_stage_context")
    if isinstance(stat_stage_context, dict) and isinstance(stat_stage_context.get("current_stages"), list):
        for stage in stat_stage_context["current_stages"]:
            if isinstance(stage, dict):
                side, stat, value = stage.get("side"), stage.get("stat"), stage.get("stage")
                if isinstance(side, str) and isinstance(stat, str) and isinstance(value, int) and not isinstance(value, bool):
                    entries.append(("current_stat_stage", side.lower(), _normalize_trusted_context_identity(stat), str(value)))
    final_stat_context = payload.get("final_stat_context")
    if isinstance(final_stat_context, dict) and isinstance(final_stat_context.get("current_final_stats"), list):
        for stat in final_stat_context["current_final_stats"]:
            if isinstance(stat, dict) and isinstance(stat.get("side"), str) and isinstance(stat.get("stat"), str) and isinstance(stat.get("value"), int):
                entries.append(("current_final_stat", stat["side"].lower(), _normalize_trusted_context_identity(stat["stat"]), str(stat["value"])))
    current_hp_context = payload.get("current_hp_context")
    if isinstance(current_hp_context, dict) and isinstance(current_hp_context.get("current_hp"), list):
        for hp in current_hp_context["current_hp"]:
            if isinstance(hp, dict) and isinstance(hp.get("side"), str) and isinstance(hp.get("current_hp"), int) and isinstance(hp.get("maximum_hp"), int):
                entries.append(("current_hp", hp["side"].lower(), str(hp["current_hp"]), str(hp["maximum_hp"])))
    field_state_context = payload.get("field_state_context")
    if isinstance(field_state_context, dict) and isinstance(field_state_context.get("current_field"), dict):
        field = field_state_context["current_field"]
        weather, terrain = field.get("weather"), field.get("terrain")
        if isinstance(weather, str):
            entries.append(("current_weather", "", _normalize_trusted_context_identity(weather), None))
        if isinstance(terrain, str):
            entries.append(("current_terrain", "", _normalize_trusted_context_identity(terrain), None))
        global_effects = field.get("global_effects")
        if isinstance(global_effects, list):
            for effect in global_effects:
                if isinstance(effect, str):
                    entries.append(("current_global_field_effect", "", _normalize_trusted_context_identity(effect), None))
        side_effects = field.get("side_effects")
        if isinstance(side_effects, list):
            for effect in side_effects:
                if isinstance(effect, dict) and isinstance(effect.get("side"), str) and isinstance(effect.get("effect"), str):
                    entries.append(("current_side_field_effect", effect["side"].lower(), _normalize_trusted_context_identity(effect["effect"]), None))
    battle_format_context = payload.get("battle_format_context")
    if isinstance(battle_format_context, dict):
        current = battle_format_context.get("current_battle_format")
        if isinstance(current, dict) and current.get("battle_format") in {"singles", "doubles"}:
            entries.append(("battle_format", "", current["battle_format"], None))
    observed = payload.get("observed_previous_damage_context")
    if isinstance(observed, dict) and all(
        observed.get(key) == value
        for key, value in (("source_side", "opponent"), ("target_side", "self"), ("damage_kind", "direct_move_damage"), ("source", "user_confirmed_previous_damage"), ("confidence", "known"))
    ) and isinstance(observed.get("damage"), int) and not isinstance(observed.get("damage"), bool) and observed.get("damage") > 0 and observed.get("damage_category") in {"physical", "special"}:
        entries.append(("observed_previous_damage", "opponent", "self", f"{observed['damage']}:{observed['damage_category']}"))
    opponent_move = _selected_opponent_move_payload_from_advice_payload(payload)
    if isinstance(opponent_move, dict) and isinstance(opponent_move.get("move_id"), str) and isinstance(opponent_move.get("priority"), int) and not isinstance(opponent_move.get("priority"), bool):
        entries.append(("opponent_move", "", opponent_move["move_id"].lower(), str(opponent_move["priority"])))
    item_event_context = payload.get("item_event_context")
    if isinstance(item_event_context, dict) and isinstance(item_event_context.get("observed_events"), list):
        for event in item_event_context["observed_events"]:
            if isinstance(event, dict):
                side, item, event_type = event.get("side"), event.get("item"), event.get("event_type")
                if isinstance(side, str) and isinstance(item, str) and isinstance(event_type, str):
                    entries.append(("observed_item_event", side.lower(), _normalize_trusted_context_identity(item), event_type.lower()))
    return tuple(entries)


def build_deterministic_result_acknowledgement_entries(payload: dict[str, Any]) -> tuple[tuple[str, ...], ...]:
    """Return result acknowledgement entries separately from user-confirmed input."""
    context = payload.get("deterministic_calculation_context")
    if not isinstance(context, dict):
        return ()
    entries: list[tuple[str, ...]] = []
    for entry in context.get("effective_stats", []):
        if isinstance(entry, dict):
            side, stat, value = entry.get("side"), entry.get("stat"), entry.get("effective_value")
            if isinstance(side, str) and isinstance(stat, str) and isinstance(value, int):
                entries.append(("effective_stat", side.lower(), _normalize_trusted_context_identity(stat), str(value), "final-stat-plus-stage"))
    comparison = context.get("speed_comparison")
    if isinstance(comparison, dict) and comparison.get("calculation_status") == "resolved":
        result, scope = comparison.get("result"), comparison.get("calculation_scope")
        if isinstance(result, str) and isinstance(scope, str):
            entries.append(("speed_comparison", "", result.replace("_", "-"), scope.replace("_", "-"), ""))
    order = context.get("move_order_assessment")
    if isinstance(order, dict):
        scope = order.get("scope")
        for side in ("self", "opponent"):
            move, priority = order.get(f"{side}_move"), order.get(f"{side}_priority")
            if isinstance(move, str) and isinstance(priority, int) and not isinstance(priority, bool):
                entries.append(("move_priority", side, move.lower(), str(priority)))
            speed = order.get(f"{side}_effective_speed")
            if isinstance(speed, int) and not isinstance(speed, bool):
                entries.append(("effective_speed", side, str(speed), "stage-tailwind-only"))
        result, reason = order.get("result"), order.get("reason")
        if isinstance(result, str) and isinstance(reason, str) and isinstance(scope, str):
            entries.append(("move_order", result.replace("_", "-"), reason.replace("_", "-"), scope.replace("_", "-")))
    hit_chance = context.get("hit_chance_assessment")
    if isinstance(hit_chance, dict):
        move, result, reason, scope = (hit_chance.get(key) for key in ("move", "result", "reason", "scope"))
        percent = hit_chance.get("hit_chance_percent")
        if all(isinstance(value, str) for value in (move, result, reason, scope)):
            display = "unavailable" if result == "unavailable" else f"{percent}%" if isinstance(percent, int) else None
            if display is not None:
                entries.append(("hit_chance", "self", "opponent", move.lower(), display, reason.replace("_", "-"), scope.replace("_", "-")))
    drain_recoil = context.get("drain_recoil_assessment")
    if isinstance(drain_recoil, dict) and drain_recoil.get("calculation_status") == "resolved":
        move, effect, percent, scope = (drain_recoil.get(key) for key in ("move", "effect", "percent", "scope"))
        amounts = drain_recoil.get("effect_amount_range")
        if isinstance(move, str) and effect in {"drain", "recoil"} and isinstance(percent, int) and isinstance(scope, str) and isinstance(amounts, dict) and all(isinstance(amounts.get(key), int) for key in ("minimum", "maximum")):
            entries.append(("drain_recoil", effect, move.lower(), f"{percent}%", f"{amounts['minimum']}-{amounts['maximum']} HP", scope.replace("_", "-")))
        restored = drain_recoil.get("actual_restored_hp_range")
        if effect == "drain" and isinstance(restored, dict) and all(isinstance(restored.get(key), int) for key in ("minimum", "maximum")):
            entries.append(("actual_healing", "self", move.lower(), f"{restored['minimum']}-{restored['maximum']} HP", "current-hp-capped"))
        if effect == "recoil" and isinstance(drain_recoil.get("recoil_ko_count"), int) and isinstance(drain_recoil.get("roll_count"), int) and isinstance(drain_recoil.get("recoil_ko_status"), str):
            entries.append(("recoil_ko", "self", move.lower(), f"{drain_recoil['recoil_ko_count']}/{drain_recoil['roll_count']}", drain_recoil["recoil_ko_status"].replace("_", "-")))
    direct_healing = context.get("direct_healing_assessment")
    if isinstance(direct_healing, dict):
        move, status, scope = (direct_healing.get(key) for key in ("move", "status", "scope"))
        percent = direct_healing.get("healing_percent")
        if isinstance(move, str) and isinstance(status, str) and isinstance(scope, str):
            if status == "resolved" and isinstance(percent, int) and all(isinstance(direct_healing.get(key), int) for key in ("actual_healing", "resulting_hp", "maximum_hp")):
                entries.append(("direct_healing", "self", move.lower(), f"{percent}%", f"{direct_healing['actual_healing']} HP", f"{direct_healing['resulting_hp']}/{direct_healing['maximum_hp']}", scope.replace("_", "-")))
            elif status == "no_effect" and isinstance(percent, int) and direct_healing.get("actual_healing") == 0 and direct_healing.get("reason") == "already_at_full_hp":
                entries.append(("direct_healing", "self", move.lower(), f"{percent}%", "0 HP", "already-at-full-hp", scope.replace("_", "-")))
            elif status in {"unavailable", "not_applicable"} and isinstance(direct_healing.get("reason"), str):
                entries.append(("direct_healing", "self", move.lower(), status.replace("_", "-"), direct_healing["reason"].replace("_", "-")))
    fixed = context.get("fixed_damage_assessment")
    if isinstance(fixed, dict) and isinstance(fixed.get("move"), str):
        if fixed.get("status") == "resolved" and isinstance(fixed.get("damage"), int) and isinstance(fixed.get("rule"), str):
            entries.append(("fixed_damage", "self", "opponent", fixed["move"].lower(), fixed["rule"].replace("_", "-"), f"{fixed['damage']} HP", fixed["scope"].replace("_", "-")))
            if isinstance(fixed.get("ko_status"), str): entries.append(("fixed_damage_ko", "self", "opponent", fixed["move"].lower(), fixed["ko_status"].replace("_", "-")))
        elif fixed.get("status") in {"unavailable", "not_applicable"} and isinstance(fixed.get("reason"), str):
            entries.append(("fixed_damage", "self", "opponent", fixed["move"].lower(), fixed["status"].replace("_", "-"), fixed["reason"].replace("_", "-")))
    special = context.get("hp_based_special_damage_assessment")
    if isinstance(special, dict) and isinstance(special.get("move"), str):
        move, status = special["move"].lower(), special.get("status")
        if status == "resolved" and isinstance(special.get("rule"), str) and isinstance(special.get("damage"), int):
            entries.append(("hp_special_damage", "self", "opponent", move, special["rule"].replace("_", "-"), f"{special['damage']} HP", special["scope"].replace("_", "-")))
            entries.append(("target_resulting_hp", "opponent", move, f"{special['opponent_resulting_hp']} HP"))
            if move == "final-gambit": entries.append(("self_faint", "self", move, "guaranteed-self-faint"))
        elif status in {"no_effect", "unavailable", "not_applicable"} and isinstance(special.get("reason"), str):
            entries.append(("hp_special_damage", "self", "opponent", move, status.replace("_", "-"), special["reason"].replace("_", "-")))
    reactive = context.get("observed_damage_counter_assessment")
    if isinstance(reactive, dict) and isinstance(reactive.get("move"), str):
        move, status, scope = reactive["move"].lower(), reactive.get("status"), reactive.get("scope")
        if status == "resolved" and isinstance(reactive.get("rule"), str) and isinstance(reactive.get("returned_damage"), int) and isinstance(scope, str):
            entries.append(("reactive_damage", "self", "opponent", move, reactive["rule"].replace("_", "-"), f"{reactive['returned_damage']} HP", scope.replace("_", "-")))
            if isinstance(reactive.get("actual_damage"), int):
                entries.append(("reactive_actual_damage", "self", "opponent", move, f"{reactive['actual_damage']} HP"))
            if isinstance(reactive.get("opponent_resulting_hp"), int):
                entries.append(("target_resulting_hp", "opponent", move, f"{reactive['opponent_resulting_hp']} HP"))
            if isinstance(reactive.get("ko_status"), str):
                entries.append(("reactive_ko", "self", "opponent", move, reactive["ko_status"].replace("_", "-")))
        elif status in {"no_effect", "unavailable", "not_applicable"} and isinstance(reactive.get("reason"), str):
            entries.append(("reactive_damage", "self", "opponent", move, status.replace("_", "-"), reactive["reason"].replace("_", "-")))
    self_consequence = context.get("self_consequence_assessment")
    if isinstance(self_consequence, dict) and isinstance(self_consequence.get("move"), str):
        move, status, scope = self_consequence["move"].lower(), self_consequence.get("status"), self_consequence.get("scope")
        if status == "resolved" and isinstance(scope, str):
            if self_consequence.get("effect") == "guaranteed_self_faint" and self_consequence.get("self_resulting_hp") == 0:
                entries.append(("self_consequence", "self", move, "guaranteed-self-faint", "0 HP", scope.replace("_", "-")))
            elif self_consequence.get("effect") == "maximum-hp-proportional-self-damage" and isinstance(self_consequence.get("self_damage"), int) and isinstance(self_consequence.get("self_resulting_hp"), int):
                entries.append(("self_damage", "self", move, f"{self_consequence['self_damage']} HP", "maximum-hp-proportional", scope.replace("_", "-")))
                entries.append(("self_resulting_hp", "self", move, f"{self_consequence['self_resulting_hp']} HP"))
                if isinstance(self_consequence.get("self_faint_status"), str): entries.append(("self_faint", "self", move, self_consequence["self_faint_status"].replace("_", "-")))
        elif status in {"unavailable", "not_applicable"} and isinstance(self_consequence.get("reason"), str):
            entries.append(("self_consequence", "self", move, status.replace("_", "-"), self_consequence["reason"].replace("_", "-")))
    power = context.get("current_hp_based_power_assessment")
    if isinstance(power, dict) and isinstance(power.get("move"), str):
        move, status = power["move"].lower(), power.get("status")
        if status == "resolved" and isinstance(power.get("effective_power"), int) and isinstance(power.get("rule"), str) and isinstance(power.get("scope"), str):
            entries.append(("current_hp_move_power", "self", move, str(power["effective_power"]), power["rule"].replace("_", "-"), power["scope"].replace("_", "-")))
        elif status in {"unavailable", "not_applicable"} and isinstance(power.get("reason"), str):
            entries.append(("current_hp_move_power", "self", move, status.replace("_", "-"), power["reason"].replace("_", "-")))
    speed_power = context.get("speed_based_power_assessment")
    if isinstance(speed_power, dict) and isinstance(speed_power.get("move"), str):
        move, status = speed_power["move"].lower(), speed_power.get("status")
        if status == "resolved" and isinstance(speed_power.get("effective_power"), int) and isinstance(speed_power.get("rule"), str) and isinstance(speed_power.get("scope"), str): entries.append(("speed_move_power", "self", move, str(speed_power["effective_power"]), speed_power["rule"].replace("_", "-"), speed_power["scope"].replace("_", "-")))
        elif status == "unavailable" and isinstance(speed_power.get("reason"), str): entries.append(("speed_move_power", "self", move, "unavailable", speed_power["reason"].replace("_", "-")))
    stage_power = context.get("stat_stage_based_power_assessment")
    if isinstance(stage_power, dict) and isinstance(stage_power.get("move"), str):
        move, status = stage_power["move"].lower(), stage_power.get("status")
        if status == "resolved" and isinstance(stage_power.get("effective_power"), int) and isinstance(stage_power.get("rule"), str) and isinstance(stage_power.get("scope"), str): entries.append(("stat_stage_move_power", "self", move, str(stage_power["effective_power"]), stage_power["rule"].replace("_", "-"), stage_power["scope"].replace("_", "-")))
        elif status == "unavailable" and isinstance(stage_power.get("reason"), str): entries.append(("stat_stage_move_power", "self", move, "unavailable", stage_power["reason"].replace("_", "-")))
    target_power = context.get("target_hp_based_power_assessment")
    if isinstance(target_power, dict) and isinstance(target_power.get("move"), str):
        move, status = target_power["move"].lower(), target_power.get("status")
        if status == "resolved" and isinstance(target_power.get("effective_power"), int) and isinstance(target_power.get("rule"), str) and isinstance(target_power.get("scope"), str): entries.append(("target_hp_move_power", "opponent", move, str(target_power["effective_power"]), target_power["rule"].replace("_", "-"), target_power["scope"].replace("_", "-")))
        elif status in {"unavailable", "not_applicable"} and isinstance(target_power.get("reason"), str): entries.append(("target_hp_move_power", "opponent", move, status.replace("_", "-"), target_power["reason"].replace("_", "-")))
    battle_counter = context.get("battle_counter_power_assessment")
    if isinstance(battle_counter, dict) and isinstance(battle_counter.get("move"), str):
        move, status = battle_counter["move"].lower(), battle_counter.get("status")
        if status == "resolved" and isinstance(battle_counter.get("counter"), int) and isinstance(battle_counter.get("effective_power"), int) and isinstance(battle_counter.get("rule"), str) and isinstance(battle_counter.get("scope"), str):
            entries.append(("battle_counter_move_power", "self", move, battle_counter["rule"].replace("_", "-"), str(battle_counter["counter"]), str(battle_counter["effective_power"]), battle_counter["scope"].replace("_", "-")))
        elif status == "unavailable" and isinstance(battle_counter.get("reason"), str):
            entries.append(("battle_counter_move_power", "self", move, "unavailable", battle_counter["reason"].replace("_", "-")))
    consecutive = context.get("consecutive_use_power_assessment")
    if isinstance(consecutive, dict) and isinstance(consecutive.get("move"), str):
        move, status = consecutive["move"].lower(), consecutive.get("status")
        if status == "resolved" and isinstance(consecutive.get("consecutive_uses"), int) and isinstance(consecutive.get("effective_power"), int) and isinstance(consecutive.get("rule"), str) and isinstance(consecutive.get("scope"), str):
            entries.append(("consecutive_use_move_power", "self", move, consecutive["rule"].replace("_", "-"), str(consecutive["consecutive_uses"]), str(consecutive["effective_power"]), consecutive["scope"].replace("_", "-")))
        elif status == "unavailable" and isinstance(consecutive.get("reason"), str):
            entries.append(("consecutive_use_move_power", "self", move, "unavailable", consecutive["reason"].replace("_", "-")))
    for estimate in context.get("damage_estimates", []):
        if isinstance(estimate, dict) and estimate.get("calculation_status") == "resolved":
            attacker, defender, move = estimate.get("attacker_side"), estimate.get("defender_side"), estimate.get("move")
            minimum, maximum, scope = estimate.get("min_damage"), estimate.get("max_damage"), estimate.get("calculation_scope")
            stab, effectiveness = estimate.get("stab"), estimate.get("type_effectiveness")
            if isinstance(stab, dict) and isinstance(stab.get("applied"), bool) and (stab.get("numerator"), stab.get("denominator")) in {(1, 1), (3, 2)} and isinstance(attacker, str) and isinstance(move, str):
                entries.append(("stab", attacker.lower(), move.lower(), "applied" if stab["applied"] else "not-applied", "1.5" if stab["applied"] else "1.0"))
            if isinstance(effectiveness, dict) and (effectiveness.get("numerator"), effectiveness.get("denominator")) in {(0, 1), (1, 4), (1, 2), (1, 1), (2, 1), (4, 1)} and isinstance(attacker, str) and isinstance(defender, str) and isinstance(move, str):
                labels = {(0, 1): "0x", (1, 4): "0.25x", (1, 2): "0.5x", (1, 1): "1x", (2, 1): "2x", (4, 1): "4x"}
                entries.append(("type_effectiveness", attacker.lower(), defender.lower(), move.lower(), labels[(effectiveness["numerator"], effectiveness["denominator"])]))
            screen = estimate.get("screen_modifier")
            if isinstance(screen, dict) and screen.get("applied") is True and isinstance(defender, str):
                identity, battle_format = screen.get("screen"), screen.get("battle_format")
                numerator, denominator = screen.get("numerator"), screen.get("denominator")
                if identity in {"reflect", "light-screen", "aurora-veil"} and battle_format in {"singles", "doubles"} and (numerator, denominator) in {(1, 2), (2, 3)}:
                    entries.append(("screen_modifier", defender.lower(), identity, battle_format, f"{numerator}/{denominator}"))
            if all(isinstance(value, str) for value in (attacker, defender, move, scope)) and all(isinstance(value, int) for value in (minimum, maximum)):
                entries.append(("damage_estimate", attacker.lower(), defender.lower(), move.lower(), f"{minimum}-{maximum}", scope.replace("_", "-")))  # type: ignore[arg-type]
    for assessment in context.get("hp_assessments", []):
        if not isinstance(assessment, dict) or assessment.get("calculation_status") != "resolved":
            continue
        attacker, defender, move = assessment.get("attacker_side"), assessment.get("defender_side"), assessment.get("move")
        minimum, maximum, scope = assessment.get("min_percent"), assessment.get("max_percent"), assessment.get("percentage_scope")
        ohko, two_hit = assessment.get("ohko"), assessment.get("two_hit_ko")
        if all(isinstance(value, str) for value in (attacker, defender, move, scope)) and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (minimum, maximum)):
            entries.append(("damage_percentage", attacker.lower(), defender.lower(), move.lower(), f"{minimum:.1f}-{maximum:.1f}", scope.replace("_", "-")))
        if isinstance(ohko, dict) and isinstance(ohko.get("successful_rolls"), int) and isinstance(ohko.get("total_rolls"), int) and isinstance(ohko.get("status"), str):
            entries.append(("ohko_assessment", attacker.lower(), defender.lower(), move.lower(), f"{ohko['successful_rolls']}/{ohko['total_rolls']}", ohko["status"]))
        if isinstance(two_hit, dict) and isinstance(two_hit.get("successful_combinations"), int) and isinstance(two_hit.get("total_combinations"), int) and isinstance(two_hit.get("status"), str) and isinstance(two_hit.get("scope"), str):
            entries.append(("two_hit_ko_assessment", attacker.lower(), defender.lower(), move.lower(), f"{two_hit['successful_combinations']}/{two_hit['total_combinations']}", two_hit["status"], two_hit["scope"]))
    return tuple(entries)


def _build_structured_trusted_context_acknowledgement_prompt_guard(payload: dict[str, Any]) -> str:
    entries = build_trusted_context_acknowledgement_entries(payload)
    result_entries = build_deterministic_result_acknowledgement_entries(payload)
    if not entries and not result_entries:
        return ""
    lines = ["[Trusted Context]"]
    for category, side, identity, event_type in entries:
        if category == "current_condition":
            lines.append(f"- Current condition | {side} | {identity}")
        elif category == "current_ability":
            lines.append(f"- Current ability | {side} | {identity}")
        elif category == "current_stat_stage":
            lines.append(f"- Current stat stage | {side} | {identity} | {int(event_type):+d}" if int(event_type) else f"- Current stat stage | {side} | {identity} | 0")
        elif category == "current_final_stat":
            lines.append(f"- Current final stat | {side} | {identity} | {event_type}")
        elif category == "current_hp":
            lines.append(f"- Current HP | {side} | {identity} | maximum {event_type}")
        elif category == "current_weather":
            lines.append(f"- Current weather | {identity}")
        elif category == "current_terrain":
            lines.append(f"- Current terrain | {identity}")
        elif category == "current_global_field_effect":
            lines.append(f"- Current global field effect | {identity}")
        elif category == "current_side_field_effect":
            lines.append(f"- Current side field effect | {side} | {identity}")
        elif category == "battle_format":
            lines.append(f"- Battle format | {identity}")
        elif category == "observed_previous_damage":
            damage, damage_category = event_type.split(":", 1)
            lines.append(f"- Previous direct damage | {side} | {identity} | {damage} HP | {damage_category} | user-confirmed")
        elif category == "opponent_move":
            lines.append(f"- Opponent move | {identity} | priority {event_type}")
        else:
            lines.append(f"- Observed item event | {side} | {identity} | {event_type}")
    if result_entries:
        lines.append("[Deterministic Results]")
        for entry in result_entries:
            category = entry[0]
            if category == "effective_stat":
                _, side, identity, value, scope = entry
                lines.append(f"- Effective stat | {side} | {identity} | {value} | {scope}")
            elif category == "speed_comparison":
                _, _, identity, value, _ = entry
                lines.append(f"- Speed comparison | {identity} | {value}")
            elif category == "stab":
                _, attacker, move, applied, multiplier = entry
                lines.append(f"- STAB | {attacker} | {move} | {applied} | {multiplier}")
            elif category == "type_effectiveness":
                _, attacker, defender, move, multiplier = entry
                lines.append(f"- Type effectiveness | {attacker} | {defender} | {move} | {multiplier}")
            elif category == "screen_modifier":
                _, side, screen, battle_format, multiplier = entry
                lines.append(f"- Screen modifier | {side} | {screen} | {battle_format} | {multiplier}")
            elif category == "move_priority":
                _, side, move, priority = entry
                lines.append(f"- Move priority | {side} | {move} | {priority}")
            elif category == "effective_speed":
                _, side, speed, scope = entry
                lines.append(f"- Effective speed | {side} | {speed} | {scope}")
            elif category == "move_order":
                _, result, reason, scope = entry
                lines.append(f"- Move order | {result} | {reason} | {scope}")
            elif category == "hit_chance":
                _, attacker, defender, move, percent, reason, scope = entry
                lines.append(f"- Hit chance | {attacker} | {defender} | {move} | {percent} | {reason} | {scope}")
            elif category == "drain_recoil":
                _, effect, move, percent, amount, scope = entry
                lines.append(f"- {'Drain' if effect == 'drain' else 'Recoil'} effect | self | {move} | {percent} | {amount} | {scope}")
            elif category == "actual_healing":
                _, side, move, amount, cap = entry
                lines.append(f"- Actual healing | {side} | {move} | {amount} | {cap}")
            elif category == "recoil_ko":
                _, side, move, count, status = entry
                lines.append(f"- Recoil KO assessment | {side} | {move} | {count} | {status}")
            elif category == "direct_healing":
                if len(entry) == 7:
                    _, side, move, percent, amount, result, scope = entry
                    lines.append(f"- Direct healing | {side} | {move} | {percent} | {amount} | {result} | {scope}")
                else:
                    _, side, move, status, reason = entry
                    lines.append(f"- Direct healing | {side} | {move} | {status} | {reason}")
            elif category == "fixed_damage":
                if len(entry) == 7:
                    _, attacker, defender, move, rule, damage, scope = entry
                    lines.append(f"- Fixed damage | {attacker} | {defender} | {move} | {rule} | {damage} | {scope}")
                else:
                    _, attacker, defender, move, status, reason = entry
                    lines.append(f"- Fixed damage | {attacker} | {defender} | {move} | {status} | {reason}")
            elif category == "fixed_damage_ko":
                _, attacker, defender, move, status = entry
                lines.append(f"- Fixed-damage KO assessment | {attacker} | {defender} | {move} | {status}")
            elif category == "hp_special_damage":
                if len(entry) == 7:
                    _, attacker, defender, move, rule, damage, scope = entry; lines.append(f"- HP-based special damage | {attacker} | {defender} | {move} | {rule} | {damage} | {scope}")
                else:
                    _, attacker, defender, move, status, reason = entry; lines.append(f"- HP-based special damage | {attacker} | {defender} | {move} | {status} | {reason}")
            elif category == "target_resulting_hp":
                _, side, move, hp = entry; lines.append(f"- Target resulting HP | {side} | {move} | {hp}")
            elif category == "self_faint":
                _, side, move, status = entry; lines.append(f"- Self-faint consequence | {side} | {move} | {status}")
            elif category == "reactive_damage":
                if len(entry) == 7:
                    _, attacker, defender, move, rule, damage, scope = entry; lines.append(f"- Reactive damage | {attacker} | {defender} | {move} | {rule} | {damage} | {scope}")
                else:
                    _, attacker, defender, move, status, reason = entry; lines.append(f"- Reactive damage | {attacker} | {defender} | {move} | {status} | {reason}")
            elif category == "reactive_actual_damage":
                _, attacker, defender, move, damage = entry; lines.append(f"- Reactive actual damage | {attacker} | {defender} | {move} | {damage}")
            elif category == "reactive_ko":
                _, attacker, defender, move, status = entry; lines.append(f"- Reactive KO assessment | {attacker} | {defender} | {move} | {status}")
            elif category == "self_consequence":
                if len(entry) == 6:
                    _, side, move, effect, hp, scope = entry; lines.append(f"- Self consequence | {side} | {move} | {effect} | {hp} | {scope}")
                else:
                    _, side, move, status, reason = entry; lines.append(f"- Self consequence | {side} | {move} | {status} | {reason}")
            elif category == "self_damage":
                _, side, move, damage, rule, scope = entry; lines.append(f"- Self damage | {side} | {move} | {damage} | {rule} | {scope}")
            elif category == "self_resulting_hp":
                _, side, move, hp = entry; lines.append(f"- Self resulting HP | {side} | {move} | {hp}")
            elif category == "current_hp_move_power":
                if len(entry) == 6:
                    _, side, move, value, rule, scope = entry; lines.append(f"- Current-HP move power | {side} | {move} | {value} | {rule} | {scope}")
                else:
                    _, side, move, status, reason = entry; lines.append(f"- Current-HP move power | {side} | {move} | {status} | {reason}")
            elif category == "speed_move_power":
                if len(entry) == 6:
                    _, side, move, value, rule, scope = entry; lines.append(f"- Speed-based move power | {side} | {move} | {value} | {rule} | {scope}")
                else:
                    _, side, move, status, reason = entry; lines.append(f"- Speed-based move power | {side} | {move} | {status} | {reason}")
            else:
                if category == "damage_estimate":
                    _, attacker, defender, move, damage_range, scope = entry
                    lines.append(f"- Damage estimate | {attacker} | {defender} | {move} | {damage_range} | {scope}")
                elif category == "damage_percentage":
                    _, attacker, defender, move, percent_range, scope = entry
                    lines.append(f"- Damage percentage | {attacker} | {defender} | {move} | {percent_range} | {scope}")
                elif category == "ohko_assessment":
                    _, attacker, defender, move, count, status = entry
                    lines.append(f"- OHKO assessment | {attacker} | {defender} | {move} | {count} | {status}")
                else:
                    _, attacker, defender, move, count, status, scope = entry
                    lines.append(f"- Two-hit KO assessment | {attacker} | {defender} | {move} | {count} | {status} | {scope}")
    lines.append("[Advice]")
    return (
        "Start the answer with exactly this short trusted-context acknowledgement format, copying every trusted input and "
        "deterministic result once without adding, omitting, inferring, merging, resolving, or changing it: "
        + "\n".join(lines)
        + " Then provide normal battle advice under [Advice]. "
    )


def _normalize_trusted_context_identity(value: str) -> str:
    return re.sub(r"[\s_]+", "-", value.strip().lower())


def parse_trusted_context_acknowledgement(response: str) -> tuple[tuple[tuple[str, str, str, str | None], ...], bool]:
    """Parse only the small acknowledgement block; do not interpret advice text."""
    block_match = re.search(r"(?im)^\[trusted context\]\s*$", response)
    if block_match is None:
        raise ValueError("trusted-context acknowledgement missing")
    remainder = response[block_match.end():]
    advice_match = re.search(r"(?im)^\[advice\]\s*$", remainder)
    if advice_match is None:
        raise ValueError("trusted-context advice delimiter missing")
    result_match = re.search(r"(?im)^\[deterministic results\]\s*$", remainder)
    start = block_match.end()
    if result_match is not None and result_match.start() < advice_match.start():
        advice_start = start + result_match.start()
    else:
        advice_start = start + advice_match.start()
    entries: list[tuple[str, str, str, str | None]] = []
    for line in response[start:advice_start].splitlines():
        if not line.strip():
            continue
        if not line.startswith("- "):
            raise ValueError("trusted-context malformed delimiter")
        parts = [part.strip() for part in line[2:].split("|")]
        if any(not part for part in parts):
            raise ValueError("trusted-context entry missing field")
        category = parts[0].lower()
        if category == "current condition" and len(parts) == 3:
            entry = ("current_condition", parts[1].lower(), parts[2].lower(), None)
        elif category == "current ability" and len(parts) == 3:
            entry = ("current_ability", parts[1].lower(), _normalize_trusted_context_identity(parts[2]), None)
        elif category == "current stat stage" and len(parts) == 4:
            try:
                stage_value = int(parts[3])
            except ValueError as exc:
                raise ValueError("trusted-context malformed entry") from exc
            if not -6 <= stage_value <= 6:
                raise ValueError("trusted-context malformed entry")
            entry = ("current_stat_stage", parts[1].lower(), _normalize_trusted_context_identity(parts[2]), str(stage_value))
        elif category == "current final stat" and len(parts) == 4:
            try:
                value = int(parts[3])
            except ValueError as exc:
                raise ValueError("trusted-context malformed entry") from exc
            if not 1 <= value <= 9999:
                raise ValueError("trusted-context malformed entry")
            entry = ("current_final_stat", parts[1].lower(), _normalize_trusted_context_identity(parts[2]), str(value))
        elif category == "current hp" and len(parts) == 4:
            try:
                current_hp, maximum_hp = int(parts[2]), int(parts[3].removeprefix("maximum "))
            except ValueError as exc:
                raise ValueError("trusted-context malformed entry") from exc
            if current_hp < 0 or maximum_hp < 1 or current_hp > maximum_hp:
                raise ValueError("trusted-context malformed entry")
            entry = ("current_hp", parts[1].lower(), str(current_hp), str(maximum_hp))
        elif category == "current weather" and len(parts) == 2:
            entry = ("current_weather", "", _normalize_trusted_context_identity(parts[1]), None)
        elif category == "current terrain" and len(parts) == 2:
            entry = ("current_terrain", "", _normalize_trusted_context_identity(parts[1]), None)
        elif category == "current global field effect" and len(parts) == 2:
            entry = ("current_global_field_effect", "", _normalize_trusted_context_identity(parts[1]), None)
        elif category == "current side field effect" and len(parts) == 3:
            entry = ("current_side_field_effect", parts[1].lower(), _normalize_trusted_context_identity(parts[2]), None)
        elif category == "battle format" and len(parts) == 2 and parts[1].lower() in {"singles", "doubles"}:
            entry = ("battle_format", "", parts[1].lower(), None)
        elif category == "previous direct damage" and len(parts) == 6 and parts[1].lower() == "opponent" and parts[2].lower() == "self" and re.fullmatch(r"[1-9]\d* HP", parts[3]) and parts[4].lower() in {"physical", "special"} and parts[5].lower() == "user-confirmed":
            entry = ("observed_previous_damage", "opponent", "self", f"{int(parts[3].split()[0])}:{parts[4].lower()}")
        elif category == "opponent move" and len(parts) == 3 and re.fullmatch(r"priority -?\d+", parts[2].lower()):
            entry = ("opponent_move", "", _normalize_trusted_context_identity(parts[1]), parts[2].lower().removeprefix("priority "))
        elif category == "observed item event" and len(parts) == 4:
            entry = ("observed_item_event", parts[1].lower(), _normalize_trusted_context_identity(parts[2]), parts[3].lower())
        else:
            raise ValueError("trusted-context malformed entry")
        if entry in entries:
            raise ValueError("trusted-context duplicate entry")
        entries.append(entry)
    return tuple(entries), bool(response[start + advice_match.end():].strip())


def validate_trusted_context_acknowledgement(
    response: str, expected_entries: tuple[tuple[str, str, str, str | None], ...]
) -> str | None:
    """Return a safe failure category or ``None`` for an exact acknowledgement."""
    try:
        acknowledged, advice_present = parse_trusted_context_acknowledgement(response)
    except ValueError as exc:
        return str(exc)
    if acknowledged != expected_entries:
        return "trusted-context entry mismatch"
    if not advice_present:
        return "trusted-context advice body missing"
    return None


def parse_deterministic_result_acknowledgement(response: str) -> tuple[tuple[tuple[str, ...], ...], bool]:
    """Parse only deterministic result lines; trusted input parsing remains separate."""
    block_match = re.search(r"(?im)^\[deterministic results\]\s*$", response)
    if block_match is None:
        raise ValueError("deterministic-results acknowledgement missing")
    advice_match = re.search(r"(?im)^\[advice\]\s*$", response[block_match.end():])
    if advice_match is None:
        raise ValueError("deterministic-results advice delimiter missing")
    start, end = block_match.end(), block_match.end() + advice_match.start()
    entries: list[tuple[str, ...]] = []
    for line in response[start:end].splitlines():
        if not line.strip():
            continue
        if not line.startswith("- "):
            raise ValueError("deterministic-results malformed delimiter")
        parts = [part.strip() for part in line[2:].split("|")]
        if any(not part for part in parts):
            raise ValueError("deterministic-results entry missing field")
        category = parts[0].lower()
        if category == "effective stat" and len(parts) == 5:
            try:
                value = int(parts[3])
            except ValueError as exc:
                raise ValueError("deterministic-results malformed entry") from exc
            if value < 0 or parts[4].lower() != "final-stat-plus-stage":
                raise ValueError("deterministic-results malformed entry")
            entry = ("effective_stat", parts[1].lower(), _normalize_trusted_context_identity(parts[2]), str(value), "final-stat-plus-stage")
        elif category == "speed comparison" and len(parts) == 3:
            result, scope = parts[1].lower().replace("_", "-"), parts[2].lower()
            if result not in {"self-faster", "opponent-faster", "tie"} or scope != "stage-only":
                raise ValueError("deterministic-results malformed entry")
            entry = ("speed_comparison", "", result, scope, "")
        elif category == "stab" and len(parts) == 5 and parts[3].lower() in {"applied", "not-applied"} and parts[4] in {"1.5", "1.0"}:
            if (parts[3].lower(), parts[4]) not in {("applied", "1.5"), ("not-applied", "1.0")}:
                raise ValueError("deterministic-results malformed entry")
            entry = ("stab", parts[1].lower(), _normalize_trusted_context_identity(parts[2]), parts[3].lower(), parts[4])
        elif category == "type effectiveness" and len(parts) == 5 and parts[4].lower() in {"0x", "0.25x", "0.5x", "1x", "2x", "4x"}:
            entry = ("type_effectiveness", parts[1].lower(), parts[2].lower(), _normalize_trusted_context_identity(parts[3]), parts[4].lower())
        elif category == "screen modifier" and len(parts) == 5 and parts[1].lower() in {"self", "opponent"} and _normalize_trusted_context_identity(parts[2]) in {"reflect", "light-screen", "aurora-veil"} and parts[3].lower() in {"singles", "doubles"} and parts[4] in {"1/2", "2/3"}:
            entry = ("screen_modifier", parts[1].lower(), _normalize_trusted_context_identity(parts[2]), parts[3].lower(), parts[4])
        elif category == "move priority" and len(parts) == 4 and parts[1].lower() in {"self", "opponent"} and re.fullmatch(r"-?\d+", parts[3]):
            entry = ("move_priority", parts[1].lower(), _normalize_trusted_context_identity(parts[2]), parts[3])
        elif category == "effective speed" and len(parts) == 4 and parts[1].lower() in {"self", "opponent"} and parts[2].isdigit() and parts[3].lower() == "stage-tailwind-only":
            entry = ("effective_speed", parts[1].lower(), parts[2], parts[3].lower())
        elif category == "move order" and len(parts) == 4 and parts[1].lower() in {"self-first", "opponent-first", "tie", "unavailable"} and parts[2].lower() in {"priority-advantage", "speed-advantage", "equal-priority-equal-speed", "missing-self-move-priority", "missing-opponent-move-priority", "missing-self-final-speed", "missing-opponent-final-speed", "unresolved-field-state"} and parts[3].lower() == "priority-stage-speed-tailwind-trick-room-only":
            entry = ("move_order", parts[1].lower(), parts[2].lower(), parts[3].lower())
        elif category == "hit chance" and len(parts) == 7 and parts[1].lower() == "self" and parts[2].lower() == "opponent" and parts[6].lower() == "move-accuracy-and-stages-only" and ((re.fullmatch(r"(?:100|[1-9]\d?)%", parts[4]) and parts[5].lower() in {"stage-adjusted-accuracy", "calculated-100-percent", "move-always-hits"}) or (parts[4].lower() == "unavailable" and parts[5].lower() == "missing-move-accuracy")):
            entry = ("hit_chance", "self", "opponent", _normalize_trusted_context_identity(parts[3]), parts[4].lower(), parts[5].lower(), parts[6].lower())
        elif category in {"drain effect", "recoil effect"} and len(parts) == 6 and parts[1].lower() == "self" and re.fullmatch(r"\d+%", parts[3]) and re.fullmatch(r"\d+-\d+ HP", parts[4]) and parts[5].lower() == "damage-dealt-proportional-drain-recoil-only":
            entry = ("drain_recoil", "drain" if category == "drain effect" else "recoil", _normalize_trusted_context_identity(parts[2]), parts[3], parts[4], parts[5].lower())
        elif category == "actual healing" and len(parts) == 5 and parts[1].lower() == "self" and re.fullmatch(r"\d+-\d+ HP", parts[3]) and parts[4].lower() == "current-hp-capped":
            entry = ("actual_healing", "self", _normalize_trusted_context_identity(parts[2]), parts[3], parts[4].lower())
        elif category == "recoil ko assessment" and len(parts) == 5 and parts[1].lower() == "self" and re.fullmatch(r"\d+/16", parts[3]) and parts[4].lower() in {"guaranteed-recoil-ko", "possible-recoil-ko", "no-recoil-ko"}:
            entry = ("recoil_ko", "self", _normalize_trusted_context_identity(parts[2]), parts[3], parts[4].lower())
        elif category == "direct healing" and len(parts) >= 2 and parts[1].lower() == "self":
            if len(parts) == 7 and re.fullmatch(r"\d+%", parts[3]) and re.fullmatch(r"\d+ HP", parts[4]) and re.fullmatch(r"\d+/\d+", parts[5]) and parts[6].lower() == "direct-max-hp-proportional-healing-only":
                actual, resulting = int(parts[4].split()[0]), tuple(int(value) for value in parts[5].split("/"))
                if actual < 0 or resulting[0] < 0 or resulting[0] > resulting[1] or resulting[1] < 1:
                    raise ValueError("deterministic-results malformed entry")
                entry = ("direct_healing", "self", _normalize_trusted_context_identity(parts[2]), parts[3], parts[4], parts[5], parts[6].lower())
            elif len(parts) == 7 and re.fullmatch(r"\d+%", parts[3]) and parts[4] == "0 HP" and parts[5].lower() == "already-at-full-hp" and parts[6].lower() == "direct-max-hp-proportional-healing-only":
                entry = ("direct_healing", "self", _normalize_trusted_context_identity(parts[2]), parts[3], "0 HP", "already-at-full-hp", parts[6].lower())
            elif len(parts) == 5 and parts[3].lower() in {"unavailable", "not-applicable"} and parts[4].lower() in {"unsupported-direct-healing-rule", "user-already-fainted", "missing-attacker-current-hp", "missing-attacker-maximum-hp", "invalid-attacker-hp-context", "invalid-healing-metadata"}:
                entry = ("direct_healing", "self", _normalize_trusted_context_identity(parts[2]), parts[3].lower(), parts[4].lower())
            else:
                raise ValueError("deterministic-results malformed entry")
        elif category == "fixed damage" and len(parts) >= 4 and parts[1].lower() == "self" and parts[2].lower() == "opponent":
            if len(parts) == 7 and parts[4].lower() in {"attacker-level", "literal-40", "literal-20", "defender-current-hp-half"} and re.fullmatch(r"\d+ HP", parts[5]) and parts[6].lower() == "explicit-fixed-damage-rules-only":
                entry = ("fixed_damage", "self", "opponent", _normalize_trusted_context_identity(parts[3]), parts[4].lower(), parts[5], parts[6].lower())
            elif len(parts) == 6 and parts[4].lower() in {"unavailable", "not-applicable"} and parts[5].lower() in {"unsupported-fixed-damage-rule", "missing-attacker-level", "invalid-attacker-level", "missing-defender-current-hp", "invalid-defender-current-hp", "target-already-fainted"}:
                entry = ("fixed_damage", "self", "opponent", _normalize_trusted_context_identity(parts[3]), parts[4].lower(), parts[5].lower())
            else: raise ValueError("deterministic-results malformed entry")
        elif category == "fixed-damage ko assessment" and len(parts) == 5 and parts[1].lower() == "self" and parts[2].lower() == "opponent" and parts[4].lower() in {"guaranteed-ko", "no-ko"}:
            entry = ("fixed_damage_ko", "self", "opponent", _normalize_trusted_context_identity(parts[3]), parts[4].lower())
        elif category == "target resulting hp" and len(parts) == 4 and parts[1].lower() == "opponent" and re.fullmatch(r"\d+ HP", parts[3]):
            entry = ("target_resulting_hp", "opponent", _normalize_trusted_context_identity(parts[2]), parts[3])
        elif category == "self-faint consequence" and len(parts) == 4 and parts[1].lower() == "self" and parts[3].lower() in {"guaranteed-self-faint", "no-self-faint"}:
            entry = ("self_faint", "self", _normalize_trusted_context_identity(parts[2]), parts[3].lower())
        elif category == "self consequence" and len(parts) >= 4 and parts[1].lower() == "self":
            if len(parts) == 6 and parts[3].lower() == "guaranteed-self-faint" and parts[4] == "0 HP" and parts[5].lower() == "explicit-self-sacrifice-and-hp-cost-only":
                entry = ("self_consequence", "self", _normalize_trusted_context_identity(parts[2]), "guaranteed-self-faint", "0 HP", parts[5].lower())
            elif len(parts) == 5 and parts[3].lower() in {"unavailable", "not-applicable"} and parts[4].lower() in {"unsupported-self-damage-rule", "missing-self-current-hp", "missing-self-maximum-hp", "invalid-self-hp-context", "user-already-fainted"}:
                entry = ("self_consequence", "self", _normalize_trusted_context_identity(parts[2]), parts[3].lower(), parts[4].lower())
            else: raise ValueError("deterministic-results malformed entry")
        elif category == "self damage" and len(parts) == 6 and parts[1].lower() == "self" and re.fullmatch(r"\d+ HP", parts[3]) and parts[4].lower() == "maximum-hp-proportional" and parts[5].lower() == "explicit-self-sacrifice-and-hp-cost-only":
            entry = ("self_damage", "self", _normalize_trusted_context_identity(parts[2]), parts[3], "maximum-hp-proportional", parts[5].lower())
        elif category == "self resulting hp" and len(parts) == 4 and parts[1].lower() == "self" and re.fullmatch(r"\d+ HP", parts[3]):
            entry = ("self_resulting_hp", "self", _normalize_trusted_context_identity(parts[2]), parts[3])
        elif category == "current-hp move power" and len(parts) >= 4 and parts[1].lower() == "self":
            if len(parts) == 6 and parts[3].isdigit() and parts[4].lower() in {"current-hp-proportional-150", "current-hp-power-bracket"} and parts[5].lower() == "explicit-current-hp-based-move-power-only":
                entry = ("current_hp_move_power", "self", _normalize_trusted_context_identity(parts[2]), parts[3], parts[4].lower(), parts[5].lower())
            elif len(parts) == 5 and parts[3].lower() in {"unavailable", "not-applicable"} and parts[4].lower() in {"missing-self-current-hp", "missing-self-maximum-hp", "invalid-self-hp-context", "user-already-fainted"}:
                entry = ("current_hp_move_power", "self", _normalize_trusted_context_identity(parts[2]), parts[3].lower(), parts[4].lower())
            else: raise ValueError("deterministic-results malformed entry")
        elif category == "speed-based move power" and len(parts) >= 4 and parts[1].lower() == "self":
            if len(parts) == 6 and parts[3].isdigit() and parts[4].lower() in {"self-to-opponent-speed-ratio", "opponent-to-self-speed-ratio"} and parts[5].lower() == "explicit-speed-based-move-power-only": entry = ("speed_move_power", "self", _normalize_trusted_context_identity(parts[2]), parts[3], parts[4].lower(), parts[5].lower())
            elif len(parts) == 5 and parts[3].lower() == "unavailable": entry = ("speed_move_power", "self", _normalize_trusted_context_identity(parts[2]), "unavailable", parts[4].lower())
            else: raise ValueError("deterministic-results malformed entry")
        elif category == "reactive damage" and len(parts) >= 4 and parts[1].lower() == "self" and parts[2].lower() == "opponent":
            if len(parts) == 7 and parts[4].lower() in {"double-observed-physical-damage", "double-observed-special-damage", "floor-three-halves-observed-damage"} and re.fullmatch(r"\d+ HP", parts[5]) and parts[6].lower() == "trusted-observed-direct-damage-counter-only":
                entry = ("reactive_damage", "self", "opponent", _normalize_trusted_context_identity(parts[3]), parts[4].lower(), parts[5], parts[6].lower())
            elif len(parts) == 6 and parts[4].lower() in {"no-effect", "unavailable", "not-applicable"} and parts[5].lower() in {"previous-damage-not-physical", "previous-damage-not-special", "missing-observed-previous-damage", "invalid-observed-previous-damage", "missing-previous-damage-category", "invalid-opponent-current-hp", "target-already-fainted", "type-immunity"}:
                entry = ("reactive_damage", "self", "opponent", _normalize_trusted_context_identity(parts[3]), parts[4].lower(), parts[5].lower())
            else: raise ValueError("deterministic-results malformed entry")
        elif category == "reactive actual damage" and len(parts) == 5 and parts[1].lower() == "self" and parts[2].lower() == "opponent" and re.fullmatch(r"\d+ HP", parts[4]):
            entry = ("reactive_actual_damage", "self", "opponent", _normalize_trusted_context_identity(parts[3]), parts[4])
        elif category == "reactive ko assessment" and len(parts) == 5 and parts[1].lower() == "self" and parts[2].lower() == "opponent" and parts[4].lower() in {"guaranteed-ko", "no-ko"}:
            entry = ("reactive_ko", "self", "opponent", _normalize_trusted_context_identity(parts[3]), parts[4].lower())
        elif category == "damage estimate" and len(parts) == 6:
            range_match = re.fullmatch(r"(\d+)-(\d+)", parts[4])
            if range_match is None or parts[5].lower() not in {"base-damage-stage-only", "base-damage-stage-stab-type", "base-damage-stage-stab-type-context"}:
                raise ValueError("deterministic-results malformed entry")
            minimum, maximum = int(range_match.group(1)), int(range_match.group(2))
            if minimum < 0 or minimum > maximum:
                raise ValueError("deterministic-results malformed entry")
            entry = ("damage_estimate", parts[1].lower(), parts[2].lower(), _normalize_trusted_context_identity(parts[3]), f"{minimum}-{maximum}", parts[5].lower())
        elif category == "damage percentage" and len(parts) == 6:
            range_match = re.fullmatch(r"(\d+(?:\.\d)?)-(\d+(?:\.\d)?)", parts[4])
            if range_match is None or parts[5].lower() not in {"base-damage-stage-only", "base-damage-stage-stab-type", "base-damage-stage-stab-type-context"} or float(range_match.group(1)) > float(range_match.group(2)):
                raise ValueError("deterministic-results malformed entry")
            entry = ("damage_percentage", parts[1].lower(), parts[2].lower(), _normalize_trusted_context_identity(parts[3]), f"{float(range_match.group(1)):.1f}-{float(range_match.group(2)):.1f}", parts[5].lower())
        elif category == "ohko assessment" and len(parts) == 6:
            count_match = re.fullmatch(r"(\d+)/16", parts[4])
            if count_match is None or not 0 <= int(count_match.group(1)) <= 16 or parts[5].lower() not in {"guaranteed", "possible", "impossible"}:
                raise ValueError("deterministic-results malformed entry")
            entry = ("ohko_assessment", parts[1].lower(), parts[2].lower(), _normalize_trusted_context_identity(parts[3]), f"{int(count_match.group(1))}/16", parts[5].lower())
        elif category == "two-hit ko assessment" and len(parts) == 7:
            count_match = re.fullmatch(r"(\d+)/256", parts[4])
            if count_match is None or not 0 <= int(count_match.group(1)) <= 256 or parts[5].lower() not in {"guaranteed", "possible", "impossible"} or parts[6].lower() != "two-hit-independent-rolls-no-between-turn-effects":
                raise ValueError("deterministic-results malformed entry")
            entry = ("two_hit_ko_assessment", parts[1].lower(), parts[2].lower(), _normalize_trusted_context_identity(parts[3]), f"{int(count_match.group(1))}/256", parts[5].lower(), parts[6].lower())
        else:
            raise ValueError("deterministic-results malformed entry")
        if entry in entries:
            raise ValueError("deterministic-results duplicate entry")
        entries.append(entry)
    return tuple(entries), bool(response[start + advice_match.end():].strip())


def validate_deterministic_result_acknowledgement(
    response: str, expected_entries: tuple[tuple[str, ...], ...]
) -> str | None:
    try:
        acknowledged, advice_present = parse_deterministic_result_acknowledgement(response)
    except ValueError as exc:
        return str(exc)
    if acknowledged != expected_entries:
        return "deterministic-results entry mismatch"
    if not advice_present:
        return "deterministic-results advice body missing"
    return None


def evaluate_deterministic_result_response(
    response: str,
    expected_trusted_entries: tuple[tuple[str, str, str, str | None], ...],
    expected_result_entries: tuple[tuple[str, ...], ...],
) -> str | None:
    """Validate exact result acknowledgement plus the stage-only advice boundary."""
    if failure := validate_trusted_context_acknowledgement(response, expected_trusted_entries):
        return failure
    if failure := validate_deterministic_result_acknowledgement(response, expected_result_entries):
        return failure
    advice_match = re.search(r"(?ims)^\[advice\]\s*$([\s\S]*)", response)
    advice = advice_match.group(1) if advice_match else ""
    forbidden = (
        r"\b(will|must|guaranteed to) move first\b",
        r"\b(choice scarf.*(?:applied|included))\b",
        r"\b(speed tie.*(?:wins|winner)|exact (?:damage|ko)|(?:guaranteed|confirmed) (?:ohko|2hko)|remaining hp)\b",
        r"\b(?:stab|type effectiveness|choice specs|light screen|critical hit).*(?:applied|included|reflected)\b",
        r"\b(?:levitate|flash fire|water absorb|adaptability|protean|libero|tera|air balloon|mold breaker)\b.*\b(?:applied|included|reflected|overrid)",
        r"\b(?:infiltrator|brick break|psychic fangs|critical[- ]hit screen bypass|light clay|screen expiration|next-turn persistence|ability/item override)\b",
        r"\b(?:quick claw|choice scarf|prankster|gale wings|triage|stall|lagging tail|full incense|custap berry)\b.*\b(?:first|priority|applied|included)\b",
        r"\b(?:usually|normally).*(?:priority 0|priority zero)\b|\btrick room.*priority bracket\b|\btailwind.*next turn\b",
        r"\b(?:no guard|compound eyes|hustle|victory star|wide lens|zoom lens|bright powder|lax incense|gravity|lock-on|mind reader|thunder.*rain|hurricane.*rain|blizzard.*snow|ohko).*\b(?:hit|accuracy|applied|guaranteed)\b",
        r"\b100%.*(?:damage|bypass.*immunity|ignore.*immunity)\b",
        r"\b(?:leftovers|big root|synthesis.*(?:rain|sun|weather)|rest.*sleep|wish.*next turn|strength sap.*attack|expected healing|healing.*(?:accuracy|hit chance))\b",
        r"\b(?:previous damage|damage taken).*(?:infer|estimated|was|must have been)\b",
        r"\b(?:move category|physical|special).*(?:infer|estimated|must have been)\b",
        r"\b(?:same.turn|priority).*(?:counter|mirror coat|metal burst).*(?:success|works|activate)\b",
        r"\b(?:bide|shell trap|focus punch|substitute|focus sash|sturdy)\b",
        r"\b(?:indirect|status|recoil).*(?:counter|mirror coat|metal burst|previous damage)\b",
        r"\b(?:ability immunity|ability.*immunity).*(?:override|bypass|ignore)\b",
        r"\b(?:next pokemon|next pok.mon|automatically switch\w*|replacement).*(?:switch\w*|heal\w*|recover\w*)\b",
        r"\b(?:healing wish|lunar dance).*(?:next|full heal|restore)\b",
        r"\bmemento.*(?:stat|drop|next turn|subsequent)\b",
        r"\b(?:magic guard|rock head)\b.*\b(?:applied|included|prevent|negate)\b",
        r"\b(?:self.faint|self sacrifice|self damage).*(?:recoil)\b|\brecoil.*(?:self.faint|self sacrifice)\b",
    )
    if any(re.search(pattern, advice, re.IGNORECASE) for pattern in forbidden):
        return "deterministic-results semantic boundary violation"
    return None


def build_ui_selected_trusted_context_entries(battle_input: dict[str, Any], *, enable_battle_state_context: bool) -> tuple[tuple[str, str, str, str | None], ...]:
    """Extract expected acknowledgement entries from the production normalized prompt payload."""
    prompt = _build_ui_selected_prompt(battle_input, enable_battle_state_context=enable_battle_state_context)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    return build_trusted_context_acknowledgement_entries(payload)


def build_ui_selected_deterministic_result_entries(battle_input: dict[str, Any], *, enable_battle_state_context: bool) -> tuple[tuple[str, ...], ...]:
    """Extract expected deterministic result entries from the production prompt payload."""
    prompt = _build_ui_selected_prompt(battle_input, enable_battle_state_context=enable_battle_state_context)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    return build_deterministic_result_acknowledgement_entries(payload)


def _build_available_item_context_required_mention_guard(payload: dict[str, Any]) -> str:
    labels = _collect_available_item_context_labels(payload)
    if not labels:
        return ""
    context_keys = _collect_available_item_context_keys(payload)
    contexts = "; ".join(labels)
    guard = (
        "Available item contexts are present in the advice payload: "
        f"{contexts}. Mention each listed available item context at least once "
        "when it is directly relevant to the recommendation. Do not describe "
        "these available item effects as unavailable, unmodeled, not included, "
        "not reflected, no item is considered, assuming no item, without item "
        "effects, or default no-item assumption. If a damage estimate also uses "
        "default assumptions, keep that separate from the available limited item "
        "context: say the raw damage/ko_context limitations remain, but do not "
        "erase the available item context. Keep the wording limited. Do not "
        "convert the context into final KO odds, guaranteed survival, guaranteed "
        "move order, exact final stats, or final battle truth. "
    )
    for context_key in context_keys:
        metadata = ADVICE_ITEM_CONTEXT_GUARD_METADATA.get(context_key, {})
        specific_guard = metadata.get("specific_guard")
        if isinstance(specific_guard, str) and specific_guard:
            guard += specific_guard
    return guard


def _collect_available_item_context_labels(value: Any) -> list[str]:
    labels: list[str] = []
    _collect_available_item_context_labels_into(value, labels)
    return labels


def _collect_available_item_context_keys(value: Any) -> list[str]:
    keys: list[str] = []
    _collect_available_item_context_keys_into(value, keys)
    return keys


def _collect_available_item_context_labels_into(value: Any, labels: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ADVICE_ITEM_CONTEXT_KEYS and isinstance(child, dict) and child.get("available") is True:
                labels.append(_available_item_context_label(key, child))
            _collect_available_item_context_labels_into(child, labels)
    elif isinstance(value, list):
        for item in value:
            _collect_available_item_context_labels_into(item, labels)


def _collect_available_item_context_keys_into(value: Any, keys: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                key in ADVICE_ITEM_CONTEXT_KEYS
                and isinstance(child, dict)
                and child.get("available") is True
                and key not in keys
            ):
                keys.append(key)
            _collect_available_item_context_keys_into(child, keys)
    elif isinstance(value, list):
        for item in value:
            _collect_available_item_context_keys_into(item, keys)


def _available_item_context_label(context_key: str, context: dict[str, Any]) -> str:
    item = context.get("item")
    item_name = ""
    if isinstance(item, dict):
        raw_item = item.get("name_en") or item.get("item_id")
        if isinstance(raw_item, str) and raw_item:
            item_name = raw_item
    metadata = ADVICE_ITEM_CONTEXT_GUARD_METADATA.get(context_key, {})
    raw_template = metadata.get("mention_label")
    if isinstance(raw_template, str) and raw_template:
        fallback_item_name = metadata.get("fallback_item_name")
        if not isinstance(fallback_item_name, str) or not fallback_item_name:
            fallback_item_name = context_key
        return raw_template.format(item_name=item_name or fallback_item_name)
    if item_name:
        return f"{item_name} / {context_key}"
    return context_key


def _remove_unavailable_item_contexts(value: Any) -> set[str]:
    hidden_item_sides: set[str] = set()
    if isinstance(value, dict):
        for key in list(value.keys()):
            child = value[key]
            if key in ADVICE_ITEM_CONTEXT_KEYS and isinstance(child, dict) and child.get("available") is False:
                hidden_item_sides.update(_context_item_sides(child))
                del value[key]
                continue
            hidden_item_sides.update(_remove_unavailable_item_contexts(child))
    elif isinstance(value, list):
        for item in value:
            hidden_item_sides.update(_remove_unavailable_item_contexts(item))
    return hidden_item_sides


def _collect_available_item_context_sides(value: Any) -> set[str]:
    available_item_sides: set[str] = set()
    if isinstance(value, dict):
        speed_context = value.get("speed_context")
        if isinstance(speed_context, dict):
            available_item_sides.update(_speed_context_item_sides(speed_context))
        for key, child in value.items():
            if key in ADVICE_ITEM_CONTEXT_KEYS and isinstance(child, dict) and child.get("available") is True:
                available_item_sides.update(_context_item_sides(child))
            available_item_sides.update(_collect_available_item_context_sides(child))
    elif isinstance(value, list):
        for item in value:
            available_item_sides.update(_collect_available_item_context_sides(item))
    return available_item_sides


def _speed_context_item_sides(speed_context: dict[str, Any]) -> set[str]:
    if speed_context.get("available") is not True:
        return set()
    sides: set[str] = set()
    for side in ("my_active", "opponent_active"):
        side_context = speed_context.get(side)
        if not isinstance(side_context, dict):
            continue
        modifiers = side_context.get("speed_modifiers")
        if not isinstance(modifiers, list):
            continue
        if any(_is_applied_choice_scarf_modifier(modifier) for modifier in modifiers):
            sides.add(side)
    return sides


def _is_applied_choice_scarf_modifier(modifier: Any) -> bool:
    return (
        isinstance(modifier, dict)
        and modifier.get("item_id") == "choice-scarf"
        and modifier.get("applied") is True
    )


def _context_item_sides(context: dict[str, Any]) -> set[str]:
    sides = set()
    for key in ADVICE_CONTEXT_SIDE_FIELDS:
        value = context.get(key)
        if isinstance(value, str) and value:
            sides.add(value)
    return sides


def _hide_advice_hidden_item_profiles(payload: dict[str, Any], hidden_item_sides: set[str]) -> set[str]:
    item_profiles = payload.get("item_profiles")
    if not isinstance(item_profiles, dict):
        return set()

    hidden_item_ids: set[str] = set()
    for side, profile in list(item_profiles.items()):
        if not isinstance(profile, dict):
            continue
        item_id = profile.get("item_id")
        legal_status = get_legal_item_status(item_id)
        should_hide = side in hidden_item_sides or (
            profile.get("status") == "user_confirmed"
            and legal_status.get("legal") is not True
        )
        if not should_hide:
            continue
        if isinstance(item_id, str) and item_id:
            hidden_item_ids.add(item_id)
        item_profiles[side] = {
            "status": "unknown",
            "source": "advice_payload_filter",
            "item_id": None,
            "name_en": None,
            "name_ko": None,
            "effects_scope": [],
            "damage_modifier_status": "not_applicable",
        }
    return hidden_item_ids


def _hide_advice_hidden_item_effects(value: Any, hidden_item_ids: set[str]) -> None:
    if not hidden_item_ids:
        return
    if isinstance(value, dict):
        item_id = value.get("item_id")
        if isinstance(item_id, str) and item_id in hidden_item_ids:
            _scrub_advice_hidden_item_effect(value)
        for child in value.values():
            _hide_advice_hidden_item_effects(child, hidden_item_ids)
    elif isinstance(value, list):
        for item in value:
            _hide_advice_hidden_item_effects(item, hidden_item_ids)


def _hide_move_local_unavailable_type_boost_item_effects(value: Any) -> None:
    if isinstance(value, dict):
        available_item_sides = {
            side
            for key, child in value.items()
            if key in ADVICE_ITEM_CONTEXT_KEYS
            and isinstance(child, dict)
            and child.get("available") is True
            for side in _context_item_sides(child)
        }
        for context_key in ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB:
            context = value.get(context_key)
            if isinstance(context, dict) and context.get("available") is False:
                if _context_item_sides(context) & available_item_sides:
                    continue
                damage_estimate = value.get("damage_estimate")
                if isinstance(damage_estimate, dict):
                    item_effects = damage_estimate.get("item_effects")
                    attacker_item = item_effects.get("attacker_item") if isinstance(item_effects, dict) else None
                    if isinstance(attacker_item, dict):
                        _scrub_advice_hidden_item_effect(attacker_item)
        for child in value.values():
            _hide_move_local_unavailable_type_boost_item_effects(child)
    elif isinstance(value, list):
        for item in value:
            _hide_move_local_unavailable_type_boost_item_effects(item)


def _scrub_advice_hidden_item_effect(value: dict[str, Any]) -> None:
    value["item_id"] = None
    value["name_en"] = None
    value["name_ko"] = None
    value["status"] = "advice_payload_hidden"
    value["applied_effects"] = []
    value["unapplied_effects"] = []
    value.pop("effect_type", None)
    value.pop("boosted_type", None)
    value.pop("modifier", None)
    value.pop("reason", None)


def _remove_debug_only_limitations(value: Any) -> None:
    if isinstance(value, dict):
        for key in ("limitations", "notes"):
            values = value.get(key)
            if isinstance(values, list):
                value[key] = [
                    item
                    for item in values
                    if not _contains_debug_limitation_phrase(item)
                ]
        for child in value.values():
            _remove_debug_only_limitations(child)
    elif isinstance(value, list):
        for item in value:
            _remove_debug_only_limitations(item)


def _contains_debug_limitation_phrase(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(phrase in lowered for phrase in DEBUG_ONLY_REASON_PHRASES)


def _log_advisor_call(
    *,
    model: str,
    usage: dict[str, int],
    game_id: str,
) -> dict[str, Any]:
    logger = TokenLogger()
    try:
        logger.log_call(
            model=model,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
            tool_name="damage_calculator",
            turn_number=1,
            game_id=game_id,
        )
        return logger.get_session_summary()
    except Exception as exc:  # pragma: no cover - defensive UI resilience path
        return {
            "total_calls": 0,
            "total_input_tokens": usage.get("input_tokens", 0),
            "total_output_tokens": usage.get("output_tokens", 0),
            "total_cached_tokens": usage.get("cached_tokens", 0),
            "estimated_cost_usd": 0.0,
            "pricing_status": UNKNOWN_MODEL_OR_UNKNOWN_PRICING,
            "pricing_status_counts": {UNKNOWN_MODEL_OR_UNKNOWN_PRICING: 1},
            "by_tool": {},
            "token_logging_error": str(exc),
        }
