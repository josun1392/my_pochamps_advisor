"""Opt-in coordinator-only, episode-frozen opponent slot schedules. No PPO/RNG."""
from copy import deepcopy
from collections import Counter
from advisor.learned_encoder import fingerprint

VERSION = "foundation-two-group-opponent-schedule-v1"
BASELINE = ("max_power", "champions_heuristic", "tactical_heuristic", "previous",
            "historical", "league_s0", "league_s0", "league_s0", "league_anchor", "league_anchor")
COMPETITIVE = ("champions_heuristic", "tactical_heuristic", "previous", "historical", "league_s0", "league_anchor")


def two_group_schedule():
    return {"schema_version": VERSION, "progress": "completed_trained_rollouts_in_current_experiment",
        "selection": "case_index_mod_stage_slots", "episode_boundary": "freeze_until_native_episode_ends",
        "trained_transition_budget": 65536,
        "stages": [{"start": 0, "slots": ["max_power"]*6 + list(BASELINE[1:])},
                   {"start": 32768, "slots": list(BASELINE)}]}


def validate_schedule(schedule, opponents):
    if schedule != two_group_schedule() or tuple(opponents) != BASELINE:
        raise ValueError("unsupported_two_group_opponent_schedule")
    return deepcopy(schedule)


def stage_selection(schedule, opponents, index, trained):
    if type(index) is not int or index < 0 or type(trained) is not int or trained < 0:
        raise ValueError("invalid_opponent_schedule_cursor")
    if schedule is None:
        slots, stage, identity = tuple(opponents), None, None
    else:
        validate_schedule(schedule, opponents)
        if trained > 65536:
            raise ValueError("opponent_schedule_budget_exceeded")
        stage = int(trained >= 32768)
        slots, identity = schedule["stages"][stage]["slots"], fingerprint(schedule)
    selected = slots[index % len(slots)]
    return selected, {"mechanism": "case_index_mod_slots", "stage": stage,
        "assigned_at_trained_transitions": trained, "slot_index": index % len(slots),
        "slots": list(slots), "probabilities": {k:v/len(slots) for k,v in Counter(slots).items()},
        "schedule_fingerprint": identity, "opponent": selected,
        "scope": "coordinator_only_not_policy_observation_or_info"}


def next_boundary(schedule, trained, maximum):
    if schedule is None:
        return maximum
    validate_schedule(schedule, BASELINE)
    return min(maximum, next((s["start"]-trained for s in schedule["stages"] if s["start"]>trained), maximum))
