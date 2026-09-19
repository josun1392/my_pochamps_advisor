from advisor.canonical_fling_berry_target_intrinsic_on_eat_suppression import (
    resolve_canonical_fling_berry_target_intrinsic_on_eat_suppression_contract,
    resolve_canonical_target_item_ignore_klutz,
)
from llm.advisor_detached_berry_eaten_transition import (
    materialize_detached_fling_berry_eaten_transition,
)
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    assess_fling_berry_target_eat_item_consequence_readiness,
    assess_fling_berry_target_intrinsic_on_eat_readiness,
    freeze_runtime_d0_fling_berry_eat_item_interaction_authority,
)
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import (
    _fixture,
    _leaf,
)


def _interaction(*, target_ability="pressure", target_item="__unknown__"):
    _state, snapshot, d0, actor, target, execution = _fixture(
        target_ability=target_ability,
        target_item=target_item,
    )
    leaf = _leaf(d0, actor, target, execution)
    interaction = freeze_runtime_d0_fling_berry_eat_item_interaction_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        fling_execution_authority=execution,
        actor=actor,
        target=target,
        phase="post_hit_target_berry_interaction",
        source_leaf=leaf,
    )
    return snapshot, d0, actor, target, execution, leaf, interaction


def test_pinned_contract_and_exact_ignore_klutz_set():
    contract = resolve_canonical_fling_berry_target_intrinsic_on_eat_suppression_contract()
    assert contract["status"] == "resolved"
    assert contract["source_provenance"]["battle_sha256"] == (
        "1d413692d0ed518e992593c0644a5456ab5497cbf3baf2542e65d9fba8d054b1"
    )
    assert contract["source_provenance"]["single_event_item_callback_suppression"] == (
        "target_ignoring_item_returns_existing_relay_value"
    )
    assert set(contract["ignore_klutz_showdown_item_ids"]) == {
        "abilityshield", "machobrace", "poweranklet", "powerband",
        "powerbelt", "powerbracer", "powerlens", "powerweight",
    }


def test_ignore_klutz_true_false_item_identity_is_pinned():
    shield = resolve_canonical_target_item_ignore_klutz("ability-shield")
    leftovers = resolve_canonical_target_item_ignore_klutz("leftovers")
    assert shield["status"] == "resolved" and shield["ignore_klutz"] is True
    assert leftovers["status"] == "resolved" and leftovers["ignore_klutz"] is False


def test_non_klutz_target_executes_without_item_resolution():
    *_, interaction = _interaction(target_ability="pressure", target_item="__unknown__")
    intrinsic = assess_fling_berry_target_intrinsic_on_eat_readiness(interaction)
    assert interaction["status"] == "resolved"
    assert interaction["target_eat_occurred"] is True
    assert interaction["target_eat_item_dispatched"] is True
    assert intrinsic["status"] == "resolved", intrinsic
    assert intrinsic["readiness"] == "executes"
    assert intrinsic["authority"]["target_item_authority"] == {"status": "not_required"}


def test_target_klutz_known_absent_suppresses_intrinsic_but_eat_and_ateberry_remain():
    _snapshot, d0, _actor, target, _execution, leaf, interaction = _interaction(
        target_ability="klutz", target_item=None,
    )
    intrinsic = assess_fling_berry_target_intrinsic_on_eat_readiness(interaction)
    direct = assess_fling_berry_target_eat_item_consequence_readiness(interaction)
    assert interaction["status"] == "resolved"
    assert interaction["target_eat_occurred"] is True
    assert interaction["target_eat_item_dispatched"] is True
    assert intrinsic["status"] == "resolved"
    assert intrinsic["readiness"] == "suppressed_by_target_klutz"
    assert direct["status"] == "resolved" and direct["readiness"] == "ready"
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=d0,
        source_leaf=leaf,
        interaction_authority=interaction,
        target=target,
    )
    assert eaten["status"] == "resolved"
    assert eaten["resulting_state"] == "known_true"


def test_target_klutz_known_false_item_suppresses_and_ability_shield_executes():
    *_, suppressed = _interaction(target_ability="klutz", target_item="leftovers")
    *_, executes = _interaction(target_ability="klutz", target_item="ability-shield")
    suppressed_ready = assess_fling_berry_target_intrinsic_on_eat_readiness(suppressed)
    executes_ready = assess_fling_berry_target_intrinsic_on_eat_readiness(executes)
    assert suppressed_ready["status"] == "resolved"
    assert suppressed_ready["readiness"] == "suppressed_by_target_klutz"
    assert suppressed_ready["authority"]["target_item_ignore_klutz_authority"]["ignore_klutz"] is False
    assert executes_ready["status"] == "resolved"
    assert executes_ready["readiness"] == "executes"
    assert executes_ready["authority"]["target_item_ignore_klutz_authority"]["ignore_klutz"] is True


def test_target_klutz_unknown_item_is_incomplete_not_guessed():
    *_, interaction = _interaction(target_ability="klutz", target_item="__unknown__")
    intrinsic = assess_fling_berry_target_intrinsic_on_eat_readiness(interaction)
    assert interaction["status"] == "resolved"
    assert interaction["target_eat_occurred"] is True
    assert interaction["target_eat_item_dispatched"] is True
    assert intrinsic["status"] == "incomplete"
    assert intrinsic["readiness"] == "incomplete"
    assert intrinsic["reason"] == "target_klutz_current_held_item_unknown"


def test_forged_ignore_klutz_item_classification_rejects():
    *_, interaction = _interaction(target_ability="klutz", target_item="leftovers")
    forged = dict(interaction)
    nested = dict(interaction["target_intrinsic_berry_on_eat"])
    nested["state"] = "executes"
    nested["target_item_ignore_klutz_authority"] = {
        **nested["target_item_ignore_klutz_authority"],
        "ignore_klutz": True,
    }
    forged["target_intrinsic_berry_on_eat"] = nested
    assert assess_fling_berry_target_intrinsic_on_eat_readiness(forged)["status"] == "rejected"


def test_source_klutz_and_magic_room_fail_before_target_eat():
    cases = (
        _fixture(source_ability="klutz"),
        _fixture(magic_room="active"),
    )
    expected = ("failed_klutz", "failed_item_suppressed")
    for fixture, outcome in zip(cases, expected):
        _state, snapshot, d0, actor, target, execution = fixture
        assert execution["status"] == "resolved"
        assert execution["outcome"] == outcome
        leaf = _leaf(d0, actor, target, execution)
        interaction = freeze_runtime_d0_fling_berry_eat_item_interaction_authority(
            strategy_d0=d0,
            runtime_snapshot=snapshot,
            fling_execution_authority=execution,
            actor=actor,
            target=target,
            phase="post_hit_target_berry_interaction",
            source_leaf=leaf,
        )
        assert interaction["status"] == "resolved"
        assert interaction["outcome"] == "post_hit_target_eat_not_reached"
        assert interaction["target_eat_occurred"] is False
        assert interaction["target_eat_item_dispatched"] is False


def test_no_eat_leaf_has_no_ateberry_transition():
    _state, snapshot, d0, actor, target, execution = _fixture()
    leaf = _leaf(
        d0, actor, target, execution,
        hit_state="miss", damage=0, hp=100, ko=False,
    )
    interaction = freeze_runtime_d0_fling_berry_eat_item_interaction_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        fling_execution_authority=execution,
        actor=actor,
        target=target,
        phase="post_hit_target_berry_interaction",
        source_leaf=leaf,
    )
    assert interaction["status"] == "resolved"
    assert interaction["outcome"] == "post_hit_target_eat_not_reached"
    assert interaction["target_eat_occurred"] is False
    eaten = materialize_detached_fling_berry_eaten_transition(
        strategy_d0=d0,
        source_leaf=leaf,
        interaction_authority=interaction,
        target=target,
    )
    assert eaten["status"] == "not_applicable"
