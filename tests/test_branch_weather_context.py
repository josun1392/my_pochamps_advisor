from copy import deepcopy

from llm.advisor_branch_weather_context import apply_supported_switch_entry_weather, project_field_weather
from llm.advisor_transition_preview import fingerprint_transition_preview_state


def _branch():
    owner = lambda side, pokemon: {"session_id": "weather-s", "side": side, "slot_index": 0, "pokemon_id": pokemon, "current_hp": 100, "max_hp": 100, "fainted": False}
    return {"schema_version": "deterministic-transition-preview-v1", "active": {"self": owner("self", "rain-setter"), "opponent": owner("opponent", "target")}, "current_state": {"current_state_session_id": "weather-s"}}


def test_field_weather_projection_is_detached_and_preserves_unknown_without_defaulting():
    branch = _branch(); before = deepcopy(branch); source = fingerprint_transition_preview_state(branch)
    projected = project_field_weather(branch_state=branch, source_fingerprint=source, frozen_field_state={"current_field": {"weather": "unknown", "side_effects": []}})
    assert projected["status"] == "resolved"
    assert branch == before
    state = projected["next_state"]
    assert state["branch_field_weather_context"] == {"schema_version": "detached-field-weather-v1", "session_id": "weather-s", "scope": "battle_field", "source_branch_fingerprint": source, "provenance": "frozen_field_state_context", "weather": "unknown"}
    assert state["current_state"]["field_state_context"]["current_field"]["weather"] == "unknown"
    assert project_field_weather(branch_state=branch, source_fingerprint="stale", frozen_field_state={"current_field": {"weather": "none"}}) == {"status": "rejected", "reason": "stale_source_branch"}


def test_drizzle_rain_requires_exact_projected_field_authority_and_creates_generation():
    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    projected = project_field_weather(branch_state=branch, source_fingerprint=source, frozen_field_state={"current_field": {"weather": "none", "side_effects": []}})
    state, projected_fp = projected["next_state"], projected["resulting_branch_fingerprint"]
    rain = apply_supported_switch_entry_weather(branch_state=state, source_fingerprint=projected_fp, weather_result={"status": "complete", "outcome": "weather_set", "weather_before": "none", "weather_after": "rain"})
    assert rain["status"] == "resolved"
    assert rain["resulting_branch_fingerprint"] != projected_fp
    assert rain["next_state"]["branch_field_weather_context"]["weather"] == "rain"
    foreign = deepcopy(state); foreign["branch_field_weather_context"]["session_id"] = "other"
    foreign_fp = fingerprint_transition_preview_state(foreign)
    assert apply_supported_switch_entry_weather(branch_state=foreign, source_fingerprint=foreign_fp, weather_result={"status": "complete", "outcome": "weather_set", "weather_before": "none", "weather_after": "rain"}) == {"status": "rejected", "reason": "invalid_field_weather_authority"}


def test_supported_switch_entry_weather_reuses_field_seam_for_drought_sun_only():
    branch = _branch(); source = fingerprint_transition_preview_state(branch)
    projected = project_field_weather(branch_state=branch, source_fingerprint=source, frozen_field_state={"current_field": {"weather": "rain", "side_effects": []}})
    sun = apply_supported_switch_entry_weather(branch_state=projected["next_state"], source_fingerprint=projected["resulting_branch_fingerprint"], weather_result={"status": "complete", "outcome": "weather_set", "weather_before": "rain", "weather_after": "sun"})
    assert sun["status"] == "resolved"
    assert sun["next_state"]["branch_field_weather_context"]["weather"] == "sun"
    assert sun["next_state"]["current_state"]["field_state_context"]["current_field"]["weather"] == "sun"
    rejected = apply_supported_switch_entry_weather(branch_state=projected["next_state"], source_fingerprint=projected["resulting_branch_fingerprint"], weather_result={"status": "complete", "outcome": "weather_set", "weather_before": "rain", "weather_after": "snow"})
    assert rejected == {"status": "rejected", "reason": "invalid_switch_entry_weather_result"}
