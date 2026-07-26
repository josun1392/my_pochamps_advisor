from copy import deepcopy
import ast
import inspect

import pytest

import llm.advisor_initial_battle_state as factory_module
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_battle_state_store import _valid_state
from llm.advisor_observation_replay_persistence_commands import ObservationReplayPersistenceCommands
from llm.advisor_observation_replay_runtime import ObservationReplayRuntime
from llm.advisor_reducer_state_model import UNKNOWN_BATTLE_FACT, make_unknown_battle_fact, state_fingerprint


def bootstrap(session="bootstrap"):
    result = create_unknown_bootstrap_battle_state(session, {"pokemon_id": "pikachu"}, {"pokemon_id": "eevee"})
    assert result["status"] == "initial_state_ready"
    return result["state"]


def unknown(value):
    return value == UNKNOWN_BATTLE_FACT


def values(runtime):
    read = runtime.read_state()
    return deepcopy(read["state"]), read["state_fingerprint"], read["state"]["last_applied_observation_sequence"], runtime.read_applied_ledger()


def hp_event(sequence=1, after=40):
    return {
        "event_kind": "exact_hp_transition_observed", "reducer_eligibility": "candidate",
        "observation_id": "hp", "observation_sequence": sequence, "session_id": "bootstrap",
        "side": "self", "slot_index": 0, "pokemon_id": "pikachu",
        "hp_before": 80, "hp_after": after, "payload": {"hp_before": 80, "hp_after": after},
    }


def snapshot(*events):
    return {"status": "ready", "session_id": "bootstrap", "ordered_observations": list(events)}


def test_unknown_bootstrap_factory_uses_only_explicit_selected_identity():
    state = bootstrap()
    assert state["session_id"] == "bootstrap"
    assert state["self_side"]["active_slot_index"] == 0
    assert state["self_side"]["pokemon"][0]["pokemon_id"] == "pikachu"
    assert state["opponent_side"]["pokemon"][0]["pokemon_id"] == "eevee"


def test_unknown_bootstrap_factory_marks_unconfirmed_facts_unknown():
    state = bootstrap()
    pokemon = state["self_side"]["pokemon"][0]
    assert all(unknown(pokemon[name]) for name in ("current_hp", "max_hp", "fainted", "condition", "known_item"))
    assert all(unknown(state["field"][name]) for name in ("weather", "terrain"))
    assert unknown(state["self_side"]["side_conditions"])


@pytest.mark.parametrize("self_identity,opponent_identity", [(None, "eevee"), ("pikachu", None), ({"pokemon_id": ""}, "eevee"), ({"pokemon_id": "pikachu", "extra": 1}, "eevee")])
def test_unknown_bootstrap_factory_rejects_missing_identity_without_guessing(self_identity, opponent_identity):
    assert create_unknown_bootstrap_battle_state("bootstrap", self_identity, opponent_identity) == {"status": "invalid_initial_state", "session_id": None, "state": None}


def test_unknown_bootstrap_factory_is_detached_and_deterministic():
    first, second = bootstrap(), bootstrap()
    assert first == second and state_fingerprint(first) == state_fingerprint(second)
    first["self_side"]["pokemon"][0]["current_hp"]["knowledge"] = "changed"
    assert unknown(second["self_side"]["pokemon"][0]["current_hp"])


def test_unknown_bootstrap_factory_performs_no_provider_network_or_filesystem_io():
    imports = ast.parse(inspect.getsource(factory_module))
    names = [alias.name for node in ast.walk(imports) if isinstance(node, ast.Import) for alias in node.names]
    names += [node.module for node in ast.walk(imports) if isinstance(node, ast.ImportFrom) and node.module]
    assert not any(name.startswith(("ui", "llm.advisor_client", "requests", "pathlib", "os")) for name in names)
    assert bootstrap()["last_applied_observation_sequence"] is None


def test_unknown_hp_is_not_encoded_as_full_or_zero_hp():
    pokemon = bootstrap()["self_side"]["pokemon"][0]
    assert unknown(pokemon["current_hp"]) and unknown(pokemon["max_hp"])
    assert pokemon["current_hp"] not in (0, 100) and pokemon["max_hp"] not in (0, 100)


def test_unknown_fainted_is_not_encoded_as_false():
    assert unknown(bootstrap()["self_side"]["pokemon"][0]["fainted"])


@pytest.mark.parametrize("path,absent", [
    (("self_side", "pokemon", 0, "known_item"), None),
    (("self_side", "pokemon", 0, "condition"), None),
    (("field", "weather"), None),
    (("self_side", "side_conditions"), []),
], ids=["item", "condition", "field", "side_conditions"])
def test_unknown_facts_differ_from_confirmed_absence(path, absent):
    _assert_unknown_differs_from_absent(path, absent)


def _assert_unknown_differs_from_absent(path, absent):
    state, known_absent = bootstrap(), bootstrap()
    unknown_value = state
    target = known_absent
    for key in path[:-1]:
        unknown_value, target = unknown_value[key], target[key]
    assert unknown(unknown_value[path[-1]])
    target[path[-1]] = absent
    assert state_fingerprint(state) != state_fingerprint(known_absent) and _valid_state(known_absent)


def test_unknown_item_differs_from_confirmed_no_item():
    _assert_unknown_differs_from_absent(("self_side", "pokemon", 0, "known_item"), None)


def test_unknown_condition_differs_from_confirmed_no_condition():
    _assert_unknown_differs_from_absent(("self_side", "pokemon", 0, "condition"), None)


def test_unknown_field_differs_from_confirmed_no_field():
    _assert_unknown_differs_from_absent(("field", "weather"), None)


def test_unknown_side_conditions_differ_from_confirmed_empty_set():
    _assert_unknown_differs_from_absent(("self_side", "side_conditions"), [])


def test_unknown_bootstrap_passes_exact_battle_state_validation():
    assert _valid_state(bootstrap())
    assert ObservationReplayRuntime.create(bootstrap())["status"] == "ready"


def test_unknown_marker_rejects_extra_or_malformed_fields():
    extra, malformed = bootstrap(), bootstrap()
    extra["self_side"]["pokemon"][0]["current_hp"] = {"knowledge": "unknown", "extra": True}
    malformed["field"]["weather"] = {"knowledge": "known"}
    assert not _valid_state(extra) and not _valid_state(malformed)
    assert ObservationReplayRuntime.create(extra)["status"] == "invalid_initial_state"


def test_unknown_marker_rejects_unsupported_fact_location():
    state = bootstrap(); state["self_side"]["active_slot_index"] = make_unknown_battle_fact()
    assert not _valid_state(state) and ObservationReplayRuntime.create(state)["status"] == "invalid_initial_state"


def test_existing_concrete_state_remains_valid():
    concrete = bootstrap()
    pokemon = concrete["self_side"]["pokemon"][0]
    pokemon.update({"current_hp": 80, "max_hp": 100, "fainted": False, "condition": None, "known_item": None})
    concrete["self_side"]["side_conditions"] = []
    concrete["field"] = {"weather": None, "terrain": None}
    assert _valid_state(concrete) and ObservationReplayRuntime.create(concrete)["status"] == "ready"


def test_partially_resolved_state_remains_valid():
    state = bootstrap(); state["self_side"]["pokemon"][0]["current_hp"] = 80
    assert _valid_state(state) and unknown(state["self_side"]["pokemon"][0]["known_item"])


def test_unknown_bootstrap_fingerprint_is_stable():
    assert state_fingerprint(bootstrap()) == state_fingerprint(deepcopy(bootstrap()))


def test_unknown_and_known_absent_have_distinct_fingerprints():
    _assert_unknown_differs_from_absent(("self_side", "pokemon", 0, "known_item"), None)


def test_detached_unknown_state_preserves_fingerprint():
    state = bootstrap(); copied = deepcopy(state)
    assert state_fingerprint(state) == state_fingerprint(copied)
    assert make_unknown_battle_fact() is not make_unknown_battle_fact()


def test_unknown_state_save_load_round_trip_preserves_fingerprint(tmp_path):
    created = ObservationReplayRuntime.create(bootstrap()); runtime = created["runtime"]
    commands = ObservationReplayPersistenceCommands.create(runtime)["commands"]
    target = tmp_path / "unknown.json"
    before = runtime.read_state()["state_fingerprint"]
    assert commands.save(target) == {"status": "save_complete"}
    loaded = commands.load(target)
    assert loaded["status"] == "load_ready"
    assert loaded["envelope"]["store"]["fingerprint"] == before


def test_runtime_accepts_unknown_bootstrap_state():
    assert ObservationReplayRuntime.create(bootstrap())["status"] == "ready"


def test_unknown_bootstrap_preview_is_non_mutating():
    runtime = ObservationReplayRuntime.create(bootstrap())["runtime"]; before = values(runtime)
    assert runtime.preview(snapshot(hp_event()))["status"] == "preview_ready"
    assert values(runtime) == before


def test_trusted_observation_can_resolve_one_unknown_fact():
    runtime = ObservationReplayRuntime.create(bootstrap())["runtime"]
    result = runtime.apply(snapshot(hp_event()))
    state, _, sequence, ledger = values(runtime)
    assert result["status"] == "applied" and state["self_side"]["pokemon"][0]["current_hp"] == 40
    assert sequence == 1 and set(ledger) == {"hp"}


def test_unrelated_unknown_facts_remain_unknown():
    runtime = ObservationReplayRuntime.create(bootstrap())["runtime"]
    assert runtime.apply(snapshot(hp_event()))["status"] == "applied"
    state = runtime.read_state()["state"]; pokemon = state["self_side"]["pokemon"][0]
    assert unknown(pokemon["max_hp"]) and unknown(pokemon["fainted"]) and unknown(pokemon["condition"])
    assert unknown(state["field"]["weather"]) and unknown(state["self_side"]["side_conditions"])


def test_unknown_bootstrap_does_not_create_false_transition_conflicts():
    runtime = ObservationReplayRuntime.create(bootstrap())["runtime"]
    assert runtime.preview(snapshot(hp_event()))["status"] == "preview_ready"


def test_unknown_state_preserves_session_sequence_and_cas_contracts():
    runtime = ObservationReplayRuntime.create(bootstrap())["runtime"]
    before = runtime.read_state()
    candidate = deepcopy(before["state"]); candidate["last_applied_observation_sequence"] = 1
    assert runtime._store.compare_and_replace(candidate, expected_session_id="bootstrap", expected_base_fingerprint="stale")["status"] == "stale_state"
    assert runtime.read_state() == before


def test_factory_never_uses_species_meta_as_current_battle_fact():
    state = create_unknown_bootstrap_battle_state("bootstrap", "pikachu", "eevee")["state"]
    assert unknown(state["self_side"]["pokemon"][0]["max_hp"])


def test_factory_never_infers_hp_condition_item_or_field():
    state = bootstrap(); pokemon = state["self_side"]["pokemon"][0]
    assert all(unknown(pokemon[key]) for key in ("current_hp", "max_hp", "condition", "known_item"))
    assert all(unknown(state["field"][key]) for key in ("weather", "terrain"))


def test_provider_output_cannot_create_authoritative_bootstrap_state():
    result = create_unknown_bootstrap_battle_state("bootstrap", {"pokemon_id": "pikachu", "provider": "value"}, "eevee")
    assert result["status"] == "invalid_initial_state" and result["state"] is None
