"""Detached, field-owned weather authority for executable Turn Engine branches."""
from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_transition_preview import fingerprint_transition_preview_state

_KNOWN_WEATHER = {"none", "rain", "sun", "sandstorm", "snow"}


def project_field_weather(*, branch_state: Mapping[str, Any], source_fingerprint: str, frozen_field_state: Mapping[str, Any]) -> dict[str, Any]:
    """Project exact frozen field weather without assigning it to a Pokémon or side."""
    if fingerprint_transition_preview_state(branch_state) != source_fingerprint:
        return _result("rejected", "stale_source_branch")
    weather = _weather(frozen_field_state)
    session = _session(branch_state)
    if weather is None or session is None:
        return _result("incomplete", "field_weather_authority")
    state = deepcopy(dict(branch_state))
    state["branch_field_weather_context"] = {
        "schema_version": "detached-field-weather-v1",
        "session_id": session,
        "scope": "battle_field",
        "source_branch_fingerprint": source_fingerprint,
        "provenance": "frozen_field_state_context",
        "weather": weather,
    }
    _sync_current_field_weather(state, frozen_field_state)
    return {"status": "resolved", "next_state": state, "resulting_branch_fingerprint": fingerprint_transition_preview_state(state)}


def apply_supported_switch_entry_weather(*, branch_state: Mapping[str, Any], source_fingerprint: str, weather_result: Mapping[str, Any]) -> dict[str, Any]:
    """Apply an exact canonical Rain/Sun/Sandstorm switch-entry result to the projected field."""
    if fingerprint_transition_preview_state(branch_state) != source_fingerprint:
        return _result("rejected", "stale_source_branch")
    context = branch_state.get("branch_field_weather_context")
    if not _valid_context(context, branch_state) or not isinstance(weather_result, Mapping):
        return _result("rejected", "invalid_field_weather_authority")
    before, after = weather_result.get("weather_before"), weather_result.get("weather_after")
    if weather_result.get("status") != "complete" or weather_result.get("outcome") != "weather_set" or before != context.get("weather") or after not in {"rain", "sun", "sandstorm"}:
        return _result("rejected", "invalid_switch_entry_weather_result")
    state = deepcopy(dict(branch_state))
    state["branch_field_weather_context"]["weather"] = after
    state["branch_field_weather_context"]["source_branch_fingerprint"] = source_fingerprint
    _sync_current_field_weather(state, state["current_state"].get("field_state_context"))
    return {"status": "resolved", "next_state": state, "resulting_branch_fingerprint": fingerprint_transition_preview_state(state)}


def _weather(value: Any) -> str | None:
    field = value.get("current_field") if isinstance(value, Mapping) else None
    weather = field.get("weather") if isinstance(field, Mapping) else None
    return weather if weather in _KNOWN_WEATHER | {"unknown"} else None


def _session(state: Mapping[str, Any]) -> str | None:
    active = state.get("active") if isinstance(state, Mapping) else None
    self_active = active.get("self") if isinstance(active, Mapping) else None
    session = self_active.get("session_id") if isinstance(self_active, Mapping) else None
    return session if isinstance(session, str) and session else None


def _valid_context(value: Any, state: Mapping[str, Any]) -> bool:
    required = {"schema_version", "session_id", "scope", "source_branch_fingerprint", "provenance", "weather"}
    return isinstance(value, Mapping) and set(value) == required and value.get("schema_version") == "detached-field-weather-v1" and value.get("session_id") == _session(state) and value.get("scope") == "battle_field" and value.get("provenance") == "frozen_field_state_context" and value.get("weather") in _KNOWN_WEATHER | {"unknown"}


def _sync_current_field_weather(state: dict[str, Any], field_state: Any) -> None:
    context = state.get("branch_field_weather_context")
    if not isinstance(context, Mapping):
        return
    current = state.get("current_state")
    if not isinstance(current, dict):
        return
    copied = deepcopy(dict(field_state)) if isinstance(field_state, Mapping) else {}
    field = copied.get("current_field")
    if not isinstance(field, Mapping):
        return
    copied["current_field"] = {**deepcopy(dict(field)), "weather": context["weather"]}
    current["field_state_context"] = copied


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "reason": reason}
