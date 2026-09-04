from copy import deepcopy

from llm.advisor_detached_leech_seed_application import materialize_detached_leech_seed_application


def _owner(side, pokemon_id): return {"session_id":"s", "side":side, "slot_index":0, "pokemon_id":pokemon_id}


def _inputs():
    actor, target = _owner("self", "a"), _owner("opponent", "b")
    d0 = {"status":"resolved", "session_id":"s", "source_runtime_fingerprint":"runtime", "strategy_preview_fingerprint":"branch", "decision_owner":actor, "active_owners":{"self":actor,"opponent":target}}
    action = {"action_id":"seed", "metadata_authority":{"metadata":{"move_id":"leech-seed","category":"status","type":"grass","accuracy":90,"priority":0}}}
    base = {"status":"resolved", "session_id":"s", "source_runtime_fingerprint":"runtime", "source_branch_fingerprint":"branch", "decision_owner":actor, "actor":actor, "target":target, "action_id":"seed", "move_id":"leech-seed"}
    return d0, action, actor, target, base


def _authority(base, **values): return {**base, "status":"resolved", **values}


def _call(*, accuracy="hit", types=("water",), seed="not_active", protection="not_applicable", reflection="not_applicable"):
    d0, action, actor, target, base = _inputs()
    return materialize_detached_leech_seed_application(
        strategy_d0=d0, action=action, actor=actor, target=target,
        accuracy_authority=_authority(base, outcome=accuracy),
        target_type_authority=_authority(base, types=list(types)),
        current_seed_authority=_authority(base, owner=target, state=seed),
        protection_authority=_authority(base, outcome=protection),
        reflection_authority=_authority(base, outcome=reflection),
    )


def test_leech_seed_application_distinguishes_hit_grass_repeat_miss_and_protection():
    assert _call()["outcome"] == "applicable"
    assert _call(types=("grass",))["reason"] == "leech_seed_target_grass_immune"
    assert _call(seed="active")["reason"] == "leech_seed_target_already_seeded"
    assert _call(accuracy="missed")["outcome"] == "missed"
    assert _call(protection="blocked")["outcome"] == "blocked"


def test_leech_seed_application_fails_closed_for_missing_and_foreign_authority():
    d0, action, actor, target, base = _inputs()
    authorities = dict(
        accuracy_authority=_authority(base, outcome="hit"), target_type_authority=_authority(base, types=["water"]),
        current_seed_authority=_authority(base, owner=target, state="not_active"), protection_authority=_authority(base, outcome="not_applicable"), reflection_authority=_authority(base, outcome="not_applicable"),
    )
    authorities["target_type_authority"] = {"status":"resolved"}
    assert materialize_detached_leech_seed_application(strategy_d0=d0, action=action, actor=actor, target=target, **authorities)["status"] == "rejected"
    authorities = deepcopy(authorities); authorities["target_type_authority"] = _authority(base, types=["water"]); authorities["accuracy_authority"]["source_branch_fingerprint"] = "foreign"
    assert materialize_detached_leech_seed_application(strategy_d0=d0, action=action, actor=actor, target=target, **authorities)["status"] == "rejected"
