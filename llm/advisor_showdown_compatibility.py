"""Versioned, detached compatibility; legacy state and replay remain untouched."""
from copy import deepcopy
from llm.advisor_champions_status_progression import valid_progression
from advisor.showdown_bridge import OBSERVATION_SCHEMA_VERSION

OBSERVATION_SCHEMA = OBSERVATION_SCHEMA_VERSION
STATUS_SCHEMA = "showdown-legacy-status-compatibility-v1"


def confirmed_absence(value, provenance, kind):
    """A bare legacy None is not an observation of absence."""
    if value not in (None, "none") or not isinstance(provenance, dict):
        return False
    event = provenance.get("event_kind")
    if kind == "item":
        return event in {"current_item_observed", "current_opponent_switch_target_combat_observed", "item_consumption_observed", "item_removed_observed"}
    if kind == "condition":
        return ((event in {"current_condition_observed", "current_opponent_switch_target_combat_observed"}
                 and provenance.get("trust") == "user_confirmed_observation" and provenance.get("condition") == "none")
                or event == "condition_removed_observed"
                or (event == "champions_status_condition_cleared_derived"
                    and provenance.get("source") == "runtime_champions_status_action_lifecycle_v1"
                    and provenance.get("trust") == "mechanics_derived_runtime" and provenance.get("condition") == "none"))
    return event == f"current_{kind}_observed" and provenance.get("trust") in {"user_confirmed_observation", "mechanics_derived_runtime"}


def legacy_status_projection(row, *, owner, condition, condition_provenance):
    """Preserve v1 units; native history must demonstrate compatibility.

    An adjusted duration is a legacy consumer attribute, never a native timer.
    No native counter is inferred from that adjusted value.
    """
    if (not valid_progression(row, owner) or row["condition"] != condition
            or row["condition_observation"] != condition_provenance):
        raise ValueError("legacy_status_progression_foreign_or_stale")
    return {"schema_version": STATUS_SCHEMA, "legacy_record": deepcopy(row),
            "interpretation": "verify_hypothetical_native_state_against_legacy_observed_attempts"}
