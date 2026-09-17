from copy import deepcopy

from llm.advisor_lifecycle_confirmation import LifecycleConfirmationBoundary, SWITCH_SOURCE, USER_TRUST
from llm.advisor_observation_collection import ObservationCollection
from llm.advisor_reducer_state_model import STATE_MODEL_VERSION, execute_atomic_transition
from llm.advisor_replay_policy import build_replay_plan
from llm.advisor_switch_entry_mechanics_derived_observation import derive_switch_entry_consequence


def _state():
    return {"state_version": STATE_MODEL_VERSION, "session_id": "s", "self_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "pikachu", "current_hp": 100, "max_hp": 100, "fainted": False, "condition": None, "stat_stages": {"speed": 0, "attack": 0}}, 1: {"pokemon_id": "raichu", "current_hp": 80, "max_hp": 100, "fainted": False, "condition": None, "stat_stages": {"speed": 0, "attack": 0, "special-attack": 0}}}, "side_conditions": []}, "opponent_side": {"active_slot_index": 0, "pokemon": {0: {"pokemon_id": "eevee", "current_hp": 100, "max_hp": 100, "fainted": False, "condition": None, "stat_stages": {"attack": 0}}}, "side_conditions": []}, "field": {"weather": None, "terrain": None}, "switch_hazard_context": {"schema_version": "switch-hazard-context-v2", "session_id": "s", "affected_side": "self", "stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 2, "sticky_web": "present"}, "last_applied_observation_sequence": None}


def _switch():
    boundary = LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}})
    result = boundary.confirm(event_kind="pokemon_switch_observed", payload={"switch_out_slot_index": 0, "switch_out_pokemon_id": "pikachu", "switch_in_slot_index": 1, "switch_in_pokemon_id": "raichu"}, session_id="s", source=SWITCH_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4, observation_id="sw")
    assert result["status"] == "confirmed"
    return boundary, result


def _derived(boundary, switch, kind, sequence, **payload):
    owner = ("self", 1, "raichu")
    if kind == "switch_entry_hazard_transition_derived": owner = ("self", None, None)
    result = derive_switch_entry_consequence(event_kind=kind, session_id="s", turn_number=4, observation_id=f"d{sequence}", observation_sequence=sequence, source_switch_observation=switch["observation"], side=owner[0], slot_index=owner[1], pokemon_id=owner[2], payload=payload)
    assert result["status"] == "confirmed"
    admitted = boundary.accept_switch_entry_derived(result)
    assert admitted["status"] == "confirmed"
    return admitted


def _plan(results):
    collection = ObservationCollection("s")
    assert collection.add_confirmation_results(results)["status"] == "added"
    return build_replay_plan(_state(), collection.snapshot()["ordered_observations"])


def _raw_plan(*results):
    return build_replay_plan(_state(), [result["observation"] for result in results])


def test_mixed_switch_entry_batch_replays_and_commits_atomically():
    boundary, switch = _switch()
    hp = _derived(boundary, switch, "switch_entry_hp_transition_derived", 2, mechanic="entry_hazards", hp_before=80, hp_after=70)
    condition = _derived(boundary, switch, "switch_entry_condition_applied_derived", 3, mechanic="toxic_spikes", condition_before=None, condition="poison")
    stage = _derived(boundary, switch, "switch_entry_stat_stage_transition_derived", 4, mechanic="sticky_web", stage_before=0, stage_after=-1, stat="speed")
    weather = _derived(boundary, switch, "switch_entry_weather_transition_derived", 5, source_ability="drizzle", weather_before=None, weather_after="rain")
    plan = _plan((switch, hp, condition, stage, weather))
    result = execute_atomic_transition(_state(), plan, expected_session_id="s")
    assert result["status"] == "committed"
    raichu = result["committed_state"]["self_side"]["pokemon"][1]
    assert (raichu["current_hp"], raichu["condition"], raichu["stat_stages"]["speed"]) == (70, "poison", -1)
    assert result["committed_state"]["field"]["weather"] == "rain"


def test_late_invalid_derived_weather_cannot_prefix_commit():
    boundary, switch = _switch()
    hp = _derived(boundary, switch, "switch_entry_hp_transition_derived", 2, mechanic="entry_hazards", hp_before=80, hp_after=70)
    condition = _derived(boundary, switch, "switch_entry_condition_applied_derived", 3, mechanic="toxic_spikes", condition_before=None, condition="toxic")
    stage = _derived(boundary, switch, "switch_entry_stat_stage_transition_derived", 4, mechanic="sticky_web", stage_before=0, stage_after=-1, stat="speed")
    weather = _derived(boundary, switch, "switch_entry_weather_transition_derived", 5, source_ability="drizzle", weather_before=None, weather_after="rain")
    bad = deepcopy(weather); bad["observation"]["payload"]["weather_before"] = "sun"
    plan = _plan((switch, hp, condition, stage, bad))
    base = _state(); before = deepcopy(base)
    result = execute_atomic_transition(base, plan, expected_session_id="s")
    assert result["status"] == "blocked_by_semantic_conflict" and result["committed_state"] is None and base == before


def test_derived_constructor_and_replay_fail_closed_for_wrong_binding_and_provenance():
    boundary, switch = _switch()
    assert derive_switch_entry_consequence(event_kind="switch_entry_hp_transition_derived", session_id="s", turn_number=4, observation_id="bad", observation_sequence=2, source_switch_observation=switch["observation"], side="self", slot_index=0, pokemon_id="pikachu", payload={"mechanic": "entry_hazards", "hp_before": 80, "hp_after": 70})["status"] == "rejected"
    hp = _derived(boundary, switch, "switch_entry_hp_transition_derived", 2, mechanic="entry_hazards", hp_before=80, hp_after=70)
    forged = deepcopy(hp); forged["observation"]["trust"] = USER_TRUST
    collection = ObservationCollection("s")
    assert collection.add_confirmation_results((switch, forged))["status"] == "invalid_observation"
    wrong_source = deepcopy(hp); wrong_source["observation"]["payload"]["source_switch_observation_id"] = "missing"
    assert _plan((switch, wrong_source))["status"] == "blocked_by_conflict"


def test_mechanic_specific_guards_reject_arbitrary_mutations():
    boundary, switch = _switch()
    for kind, payload, mutate in (
        ("switch_entry_hp_transition_derived", {"mechanic": "entry_hazards", "hp_before": 80, "hp_after": 70}, ("hp_after", 81)),
        ("switch_entry_condition_applied_derived", {"mechanic": "toxic_spikes", "condition_before": None, "condition": "poison"}, ("condition", "burn")),
        ("switch_entry_stat_stage_transition_derived", {"mechanic": "sticky_web", "stage_before": 0, "stage_after": -1, "stat": "speed"}, ("stat", "attack")),
        ("switch_entry_weather_transition_derived", {"source_ability": "drizzle", "weather_before": None, "weather_after": "rain"}, ("weather_after", "sun")),
    ):
        valid = _derived(boundary, switch, kind, boundary._next_sequence, **payload)
        forged = deepcopy(valid); forged["observation"]["payload"][mutate[0]] = mutate[1]
        plan = _plan((switch, forged))
        assert execute_atomic_transition(_state(), plan, expected_session_id="s")["status"] == "blocked_by_semantic_conflict"


def test_hazard_absorption_and_entry_hazard_ko_reuse_canonical_owners():
    boundary, switch = _switch()
    absorption = _derived(boundary, switch, "switch_entry_hazard_transition_derived", 2, hazards_before={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 2, "sticky_web": "present"}, hazards_after={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "present"})
    absorbed = execute_atomic_transition(_state(), _plan((switch, absorption)), expected_session_id="s")
    assert absorbed["status"] == "committed" and absorbed["committed_state"]["switch_hazard_context"]["toxic_spikes_layers"] == 0
    boundary, switch = _switch()
    zero = _derived(boundary, switch, "switch_entry_hp_transition_derived", 2, mechanic="entry_hazards", hp_before=80, hp_after=0)
    faint = _derived(boundary, switch, "switch_entry_faint_derived", 3, mechanic="entry_hazards")
    ko = execute_atomic_transition(_state(), _plan((switch, zero, faint)), expected_session_id="s")
    assert ko["status"] == "committed" and ko["committed_state"]["self_side"]["pokemon"][1]["fainted"] is True


def test_intimidate_download_and_all_weather_setters_are_exactly_bounded():
    boundary, switch = _switch()
    intimidate = derive_switch_entry_consequence(event_kind="switch_entry_stat_stage_transition_derived", session_id="s", turn_number=4, observation_id="i", observation_sequence=2, source_switch_observation=switch["observation"], side="opponent", slot_index=0, pokemon_id="eevee", payload={"mechanic": "intimidate", "stage_before": 0, "stage_after": -1, "stat": "attack"})
    assert boundary.accept_switch_entry_derived(intimidate)["status"] == "confirmed"
    result = execute_atomic_transition(_state(), _plan((switch, intimidate)), expected_session_id="s")
    assert result["status"] == "committed" and result["committed_state"]["opponent_side"]["pokemon"][0]["stat_stages"]["attack"] == -1
    boundary, switch = _switch()
    reversed_intimidate = derive_switch_entry_consequence(event_kind="switch_entry_stat_stage_transition_derived", session_id="s", turn_number=4, observation_id="ir", observation_sequence=2, source_switch_observation=switch["observation"], side="opponent", slot_index=0, pokemon_id="eevee", payload={"mechanic": "intimidate_reversed", "stage_before": 0, "stage_after": 1, "stat": "attack"})
    assert boundary.accept_switch_entry_derived(reversed_intimidate)["status"] == "confirmed"
    assert execute_atomic_transition(_state(), _plan((switch, reversed_intimidate)), expected_session_id="s")["committed_state"]["opponent_side"]["pokemon"][0]["stat_stages"]["attack"] == 1
    for stat in ("attack", "special-attack"):
        boundary, switch = _switch()
        download = _derived(boundary, switch, "switch_entry_stat_stage_transition_derived", 2, mechanic="download", stage_before=0, stage_after=1, stat=stat)
        assert execute_atomic_transition(_state(), _plan((switch, download)), expected_session_id="s")["status"] == "committed"
    for ability, weather in (("drizzle", "rain"), ("drought", "sun"), ("sand-stream", "sandstorm"), ("snow-warning", "snow")):
        boundary, switch = _switch()
        derived = _derived(boundary, switch, "switch_entry_weather_transition_derived", 2, source_ability=ability, weather_before=None, weather_after=weather)
        assert execute_atomic_transition(_state(), _plan((switch, derived)), expected_session_id="s")["committed_state"]["field"]["weather"] == weather


def test_source_switch_dependency_rejects_absent_ordered_stale_and_later_batch_sources():
    boundary, switch = _switch()
    hp = _derived(boundary, switch, "switch_entry_hp_transition_derived", 2, mechanic="entry_hazards", hp_before=80, hp_after=70)
    assert _raw_plan(hp)["status"] == "blocked_by_conflict"  # no source / standalone later batch
    for field, value in (("source_switch_observation_id", "missing"), ("turn_number", 5), ("observation_sequence", 1)):
        forged = deepcopy(hp); target = forged["observation"]
        if field == "source_switch_observation_id": target["payload"][field] = value
        else: target[field] = value
        assert _raw_plan(switch, forged)["status"] == "blocked_by_conflict"
    foreign = deepcopy(hp); foreign["observation"]["session_id"] = "foreign"
    plan = _raw_plan(switch, foreign)
    assert plan["ordered_steps"] == [plan["ordered_steps"][0]] and plan["excluded_events"][0]["reason"] == "invalid_session_or_sequence"
    wrong_owner = deepcopy(hp); wrong_owner["observation"].update(side="opponent", slot_index=0, pokemon_id="eevee")
    assert _raw_plan(switch, wrong_owner)["status"] == "blocked_by_conflict"


def test_hp_condition_and_faint_fail_closed_against_noncanonical_transitions():
    boundary, switch = _switch()
    hp = _derived(boundary, switch, "switch_entry_hp_transition_derived", 2, mechanic="entry_hazards", hp_before=80, hp_after=70)
    mismatch = deepcopy(hp); mismatch["observation"]["payload"]["hp_before"] = 79
    assert execute_atomic_transition(_state(), _raw_plan(switch, mismatch), expected_session_id="s")["status"] == "blocked_by_semantic_conflict"
    invalid_condition = deepcopy(_derived(boundary, switch, "switch_entry_condition_applied_derived", 3, mechanic="toxic_spikes", condition_before=None, condition="poison")); invalid_condition["observation"]["payload"]["condition"] = "burn"
    assert execute_atomic_transition(_state(), _raw_plan(switch, hp, invalid_condition), expected_session_id="s")["status"] == "blocked_by_semantic_conflict"
    faint = _derived(boundary, switch, "switch_entry_faint_derived", 4, mechanic="entry_hazards")
    assert execute_atomic_transition(_state(), _raw_plan(switch, faint), expected_session_id="s")["status"] == "blocked_by_semantic_conflict"
    zero = _derived(boundary, switch, "switch_entry_hp_transition_derived", 5, mechanic="entry_hazards", hp_before=80, hp_after=0)
    duplicate = _derived(boundary, switch, "switch_entry_faint_derived", 6, mechanic="entry_hazards")
    assert execute_atomic_transition(_state(), _raw_plan(switch, zero, faint, duplicate), expected_session_id="s")["status"] == "blocked_by_semantic_conflict"


def test_stage_weather_hazard_and_provenance_mutations_are_rejected():
    boundary, switch = _switch()
    stage = _derived(boundary, switch, "switch_entry_stat_stage_transition_derived", 2, mechanic="sticky_web", stage_before=0, stage_after=-1, stat="speed")
    for field, value in (("stage_after", -3), ("stat", "attack")):
        forged = deepcopy(stage); forged["observation"]["payload"][field] = value
        assert execute_atomic_transition(_state(), _raw_plan(switch, forged), expected_session_id="s")["status"] == "blocked_by_semantic_conflict"
    intimidate = derive_switch_entry_consequence(event_kind="switch_entry_stat_stage_transition_derived", session_id="s", turn_number=4, observation_id="i2", observation_sequence=3, source_switch_observation=switch["observation"], side="opponent", slot_index=0, pokemon_id="eevee", payload={"mechanic": "intimidate", "stage_before": 0, "stage_after": -1, "stat": "attack"})
    for field, value in (("stage_after", 1), ("pokemon_id", "missing")):
        forged = deepcopy(intimidate); (forged["observation"]["payload"] if field == "stage_after" else forged["observation"])[field] = value
        assert execute_atomic_transition(_state(), _raw_plan(switch, forged), expected_session_id="s")["status"] == "blocked_by_semantic_conflict"
    boundary, switch = _switch()
    download = _derived(boundary, switch, "switch_entry_stat_stage_transition_derived", 2, mechanic="download", stage_before=0, stage_after=1, stat="attack")
    for field, value in (("stat", "speed"), ("stage_after", 2)):
        forged = deepcopy(download); forged["observation"]["payload"][field] = value
        assert execute_atomic_transition(_state(), _raw_plan(switch, forged), expected_session_id="s")["status"] == "blocked_by_semantic_conflict"
    boundary, switch = _switch()
    weather = _derived(boundary, switch, "switch_entry_weather_transition_derived", 2, source_ability="drizzle", weather_before=None, weather_after="rain")
    for field, value in (("source_ability", "trace"), ("weather_before", "sun")):
        forged = deepcopy(weather); forged["observation"]["payload"][field] = value
        assert execute_atomic_transition(_state(), _raw_plan(switch, forged), expected_session_id="s")["status"] == "blocked_by_semantic_conflict"
    boundary, switch = _switch()
    hazard = _derived(boundary, switch, "switch_entry_hazard_transition_derived", 2, hazards_before={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 2, "sticky_web": "present"}, hazards_after={"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "present"})
    forged = deepcopy(hazard); forged["observation"]["payload"]["hazards_after"]["sticky_web"] = "absent"
    assert execute_atomic_transition(_state(), _raw_plan(switch, forged), expected_session_id="s")["status"] == "blocked_by_semantic_conflict"


def test_provenance_cannot_cross_derived_and_user_observation_families():
    boundary, switch = _switch()
    hp = _derived(boundary, switch, "switch_entry_hp_transition_derived", 2, mechanic="entry_hazards", hp_before=80, hp_after=70)
    wrong_source = deepcopy(hp); wrong_source["observation"]["source"] = "wrong"
    collection = ObservationCollection("s")
    assert collection.add_confirmation_results((switch, wrong_source))["status"] == "invalid_observation"
    ordinary = {"event_kind": "exact_hp_transition_observed", "observation_id": "ordinary", "observation_sequence": 1, "session_id": "s", "turn_number": 4, "source": "runtime_switch_entry_mechanics_v1", "trust": "mechanics_derived_runtime", "reducer_eligibility": "candidate", "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "payload": {"hp_before": 100, "hp_after": 90}}
    assert execute_atomic_transition(_state(), build_replay_plan(_state(), [ordinary]), expected_session_id="s")["status"] == "invalid_replay_plan"
