from copy import deepcopy

from advisor.canonical_fling_core import resolve_canonical_fling_core_move
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_fling_berry_eat_item_interaction_authority import (
    freeze_runtime_d0_fling_berry_eat_item_interaction_authority,
)
from llm.advisor_runtime_d0_fling_item_execution_authority import (
    freeze_runtime_d0_fling_item_execution_authority,
)
from llm.advisor_runtime_d0_fling_major_status_cure_berry_target_effect_authority import (
    freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_runtime_d0_fling_berry_eat_item_interaction_authority import (
    _fixture,
    _leaf,
)


def berry_cure_case(
    *,
    item="cheri-berry",
    condition="paralysis",
    source_ability="pressure",
    target_ability="pressure",
    hit_state="hit",
    damage=20,
    routing="target",
    hp=80,
    ko=False,
    unknown_condition=False,
):
    state, _snapshot, _d0, _actor, _target, _execution = _fixture(
        item=item,
        source_ability=source_ability,
        target_ability=target_ability,
    )
    foe = state["opponent_side"]["pokemon"][0]
    if unknown_condition:
        foe["condition"] = {"knowledge": "unknown"}
        foe.pop("condition_provenance", None)
    else:
        foe["condition"] = condition
        foe["condition_provenance"]["condition"] = condition
    snapshot = {
        "status": "runtime_snapshot_ready",
        "session_id": state["session_id"],
        "state": deepcopy(state),
        "state_fingerprint": state_fingerprint(state),
    }
    owner = {
        "session_id": state["session_id"],
        "side": "self",
        "slot_index": 0,
        "pokemon_id": state["self_side"]["pokemon"][0]["pokemon_id"],
    }
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    actor = d0["active_owners"]["self"]
    target = d0["active_owners"]["opponent"]
    metadata = resolve_canonical_fling_core_move(move={"move_id": "fling"})["metadata"]
    action = {
        "action_id": "attack:fling",
        "action_type": "attack",
        "identity": "fling",
        "move_metadata_authority": {"status": "resolved", "metadata": metadata},
    }
    execution = freeze_runtime_d0_fling_item_execution_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        action=action,
        actor=actor,
        target=target,
    )
    leaf = _leaf(
        d0,
        actor,
        target,
        execution,
        hit_state=hit_state,
        damage=damage,
        routing=routing,
        hp=hp,
        ko=ko,
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
    authority = freeze_runtime_d0_fling_major_status_cure_berry_target_effect_authority(
        strategy_d0=d0,
        runtime_snapshot=snapshot,
        fling_execution_authority=execution,
        source_leaf=leaf,
        berry_eat_item_interaction_authority=interaction,
        actor=actor,
        target=target,
    )
    return {
        "state": state,
        "snapshot": snapshot,
        "d0": d0,
        "actor": actor,
        "target": target,
        "execution": execution,
        "leaf": leaf,
        "interaction": interaction,
        "authority": authority,
    }
