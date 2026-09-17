from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_persistent_effect_state_runtime_admission import admit_current_persistent_effect_state
from llm.advisor_runtime_d0_persistent_effect_authority import project_runtime_d0_persistent_effect_branch


def _manager():
    state = create_unknown_bootstrap_battle_state("p", "self-a", "opponent-a") ["state"]
    for side in ("self_side", "opponent_side"):
        p = state[side]["pokemon"][0]
        p.update(current_hp=100, max_hp=100, fainted=False)
    return BattleObservationRuntimeSessionManager.create("p", state)["manager"]


def _admit(manager, family, value, **extra):
    return admit_current_persistent_effect_state(runtime_session_manager=manager, captured_session_id="p", family=family,
        side="self", slot_index=0, pokemon_id="self-a", persistent_state=value, turn_number=1, **extra)


def _state(manager): return manager.read_state()["state"]


def _branch(result):
    return project_runtime_d0_persistent_effect_branch(strategy_d0=result["strategy_d0"], runtime_snapshot=result["runtime_snapshot"])


def _family(branch, family):
    owner = branch["active_owners"]["self"]
    return next(row for row in branch["branch_persistent_effect_authority"]["states"] if row["family"] == family and row["owner"] == owner)


def test_current_aqua_ring_and_ingrain_are_committed_then_projected_from_fresh_d0():
    manager = _manager()
    aqua = _admit(manager, "aqua_ring", "active")
    assert aqua["status"] == "resolved"
    assert aqua["strategy_d0"]["source_runtime_fingerprint"] == aqua["runtime_snapshot"]["state_fingerprint"]
    assert _family(_branch(aqua), "aqua_ring")["state"] == "known_active"
    assert _family(_branch(aqua), "ingrain")["state"] == "unknown"
    ingrain = _admit(manager, "ingrain", "inactive")
    assert ingrain["status"] == "resolved" and _family(_branch(ingrain), "ingrain")["state"] == "known_inactive"


def test_leech_seed_source_and_replacement_are_exact():
    manager = _manager()
    active = _admit(manager, "leech_seed", "active", source_side="opponent", source_slot_index=0)
    assert active["status"] == "resolved"
    row = _family(_branch(active), "leech_seed")
    assert row["state"] == "known_active" and row["source_slot"]["side"] == "opponent"
    inactive = _admit(manager, "leech_seed", "inactive")
    assert inactive["status"] == "resolved" and _family(_branch(inactive), "leech_seed")["state"] == "known_inactive"


def test_current_state_retry_and_later_replacement_keep_one_identity_bound_row():
    manager = _manager()
    first = _admit(manager, "aqua_ring", "active")
    retry = _admit(manager, "aqua_ring", "active")
    replacement = _admit(manager, "aqua_ring", "inactive")
    assert first["status"] == retry["status"] == replacement["status"] == "resolved"
    rows = _state(manager)["current_persistent_effect_context"]["rows"]
    aqua = [row for row in rows if row["family"] == "aqua_ring" and row["owner"]["side"] == "self"]
    assert len(aqua) == 1 and aqua[0]["state"] == "inactive"


def test_rejections_have_no_prefix_mutation_and_current_active_identity_is_required():
    manager = _manager(); before = deepcopy(_state(manager))
    bad = _admit(manager, "leech_seed", "active", source_side="self", source_slot_index=0)
    assert bad["status"] == "rejected" and _state(manager) == before
    foreign = admit_current_persistent_effect_state(runtime_session_manager=manager, captured_session_id="p", family="aqua_ring", side="self", slot_index=1, pokemon_id="wrong", persistent_state="active", turn_number=1)
    assert foreign["status"] == "rejected" and _state(manager) == before
    stale = admit_current_persistent_effect_state(runtime_session_manager=manager, captured_session_id="old", family="aqua_ring", side="self", slot_index=0, pokemon_id="self-a", persistent_state="active", turn_number=1)
    assert stale["status"] == "rejected" and _state(manager) == before
