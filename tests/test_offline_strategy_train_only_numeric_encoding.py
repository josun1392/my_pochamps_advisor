"""Train-only frozen vocabularies and fixed-layout, label-blind vectors."""
from copy import deepcopy

import pytest

from llm.advisor_offline_decision_point_provenance import _freeze, fingerprint_decision_contract_reference
from llm.advisor_offline_strategy_model_feature_semantics import (
    SCHEMA_VERSION as SEMANTIC_SCHEMA,
    materialize_offline_strategy_model_feature_semantics as semantic,
    validates_detached_semantic_feature_record,
)
from llm.advisor_offline_strategy_train_only_numeric_encoding import (
    ENCODER_SCHEMA, encode_semantic_feature_record as encode,
    fit_train_only_numeric_encoder as fit,
)
from tests.test_offline_strategy_episode_dataset import _editable
from tests.test_offline_strategy_model_feature_semantics import case


def record():
    return semantic(**case()[0])


def changed(base, edit=None, *, partition=None, label=None, suffix="changed"):
    """Construct a valid detached test record; no live-source claim is made."""
    raw = _editable(base)
    if edit is not None:
        edit(raw["model_features"])
    if partition is not None:
        raw["evaluation_partition"] = partition
    if label is not None:
        raw["label"]["value"] = label
    raw["audit"]["choice_example_id"] += ":" + suffix
    if raw["model_features"] is not None:
        raw["semantic_feature_fingerprint"] = fingerprint_decision_contract_reference(raw["model_features"])
    raw["feature_record_id"] = "offline-semantic-feature:" + fingerprint_decision_contract_reference({
        "schema_version": SEMANTIC_SCHEMA, "example_id": raw["audit"]["choice_example_id"],
        "public_information_id": raw["audit"]["public_information_id"],
        "semantic_feature_fingerprint": raw["semantic_feature_fingerprint"],
    })
    result = _freeze(raw)
    assert validates_detached_semantic_feature_record(result)
    return result


def coordinate(encoder, vector, name):
    return vector[encoder["feature_layout"].index(name)]


def test_one_train_record_produces_frozen_auditable_encoder_and_vector():
    row = record()
    encoder = fit([row])
    assert encoder["status"] == "fitted", encoder
    assert encoder["schema_version"] == ENCODER_SCHEMA
    assert encoder["vector_dimension"] == len(encoder["feature_layout"]) > 0
    assert encoder["feature_layout"] == tuple(dict.fromkeys(encoder["feature_layout"]))
    assert encoder["evaluation_split_id"] == row["audit"]["evaluation_split_id"]
    assert encoder["vocabularies"]["pokemon"] == ("bench-a", "opponent-a", "self-a")
    assert "shadow-ball" in encoder["vocabularies"]["move"]
    assert "numeric_scaling_not_applied_v1" in encoder["limitations"]
    encoded = encode(encoder=encoder, semantic_record=row)
    assert encoded["status"] == "encoded", encoded
    assert len(encoded["vector"]) == encoder["vector_dimension"]
    assert encoded["label"]["value"] == 1
    assert encoded["evaluation_partition"] == "train"
    assert encoded["source_semantic_feature_fingerprint"] == row["semantic_feature_fingerprint"]
    assert all(type(value) is int for value in encoded["vector"])
    with pytest.raises(TypeError):
        encoder["vocabularies"]["pokemon"] = ()
    with pytest.raises(TypeError):
        encoded["label"]["value"] = 0


def test_train_order_and_labels_do_not_change_encoder_identity():
    a = record()
    b = changed(a, lambda f: f["public_battle"]["active"]["opponent"].update(pokemon_id="opponent-b"), suffix="b")
    first = fit([a, b])
    assert fit([b, a])["encoder_id"] == first["encoder_id"]
    assert fit([b, a])["feature_layout"] == first["feature_layout"]
    relabeled = changed(a, label=-1, suffix="relabeled")
    assert fit([relabeled, b])["encoder_id"] == first["encoder_id"]
    assert encode(encoder=first, semantic_record=a) == encode(encoder=first, semantic_record=a)


def test_validation_and_test_open_categories_map_to_oov_without_refit():
    train = record()
    encoder = fit([train])
    def novel(f):
        f["public_battle"]["active"]["opponent"]["pokemon_id"] = "validation-only-pokemon"
        f["public_battle"]["opponent_revealed_moves"]["move_ids"] = ["validation-only-move"]
        f["actor_private"]["own_roster"][0]["known_item"] = {"availability": "available", "value": "test-only-item"}
        f["actor_private"]["own_roster"][0]["current_ability"] = {"availability": "available", "value": "test-only-ability"}
    validation = changed(train, novel, partition="validation", suffix="validation")
    test = changed(train, novel, partition="test", suffix="test")
    fitted_with_holdouts = fit([train, validation, test])
    assert fitted_with_holdouts["encoder_id"] == encoder["encoder_id"]
    assert fitted_with_holdouts["feature_layout"] == encoder["feature_layout"]
    assert "validation-only-pokemon" not in encoder["vocabularies"]["pokemon"]
    assert "validation-only-move" not in encoder["vocabularies"]["move"]
    assert "test-only-item" not in encoder["vocabularies"]["item"]
    assert "test-only-ability" not in encoder["vocabularies"]["ability"]
    relabeled_validation = changed(validation, label=-1, suffix="validation-new-label")
    assert fit([train, relabeled_validation, test])["encoder_id"] == encoder["encoder_id"]
    for row in (train, validation, test):
        assert len(encode(encoder=encoder, semantic_record=row)["vector"]) == encoder["vector_dimension"]
    for row in (validation, test):
        vector = encode(encoder=encoder, semantic_record=row)["vector"]
        assert coordinate(encoder, vector, "public/active/opponent/pokemon/oov") == 1
        assert coordinate(encoder, vector, "public/revealed_moves/oov") == 1
        assert coordinate(encoder, vector, "private/roster/0/item/oov") == 1 or coordinate(encoder, vector, "private/roster/1/item/oov") == 1
        assert coordinate(encoder, vector, "private/roster/0/ability/oov") == 1 or coordinate(encoder, vector, "private/roster/1/ability/oov") == 1
    # Only moving the novel record into train permits its categories to grow the vocabulary.
    moved = changed(validation, partition="train", suffix="moved")
    expanded = fit([train, moved])
    assert expanded["encoder_id"] != encoder["encoder_id"]
    assert "validation-only-pokemon" in expanded["vocabularies"]["pokemon"]


def test_known_zero_false_missing_and_empty_item_have_distinct_coordinates():
    train = record()
    encoder = fit([train])
    known = encode(encoder=encoder, semantic_record=train)["vector"]
    assert coordinate(encoder, known, "public/active/self/current_hp/available") == 1
    assert coordinate(encoder, known, "public/active/self/current_hp/value") == 51
    assert coordinate(encoder, known, "public/active/self/stage/attack/available") == 1
    assert coordinate(encoder, known, "public/active/self/stage/attack/value") == 0
    assert coordinate(encoder, known, "public/active/self/fainted/available") == 1
    assert coordinate(encoder, known, "public/active/self/fainted/value") == 0
    assert coordinate(encoder, known, "public/trick_room/available") == 1
    assert coordinate(encoder, known, "public/trick_room/value") == 0
    assert any(coordinate(encoder, known, f"private/roster/{i}/move/{j}/pp/available") == 1
               and coordinate(encoder, known, f"private/roster/{i}/move/{j}/pp/value") == 0
               for i in range(6) for j in range(4))
    assert any(coordinate(encoder, known, f"private/roster/{i}/item/known_empty") == 1 for i in range(6))
    def make_missing(f):
        active = f["public_battle"]["active"]["self"]
        active["stat_stages"]["attack"] = {"availability": "unavailable"}
        active["fainted"] = {"availability": "unavailable"}
        f["public_battle"]["field"]["trick_room"] = {"availability": "unavailable"}
        for row in f["actor_private"]["own_roster"]:
            row["known_item"] = {"availability": "unavailable"}
            for move in row["moves"]:
                move["current_pp"] = {"availability": "unavailable"}
    missing = changed(train, make_missing, partition="validation", suffix="missing")
    unknown = encode(encoder=encoder, semantic_record=missing)["vector"]
    assert coordinate(encoder, unknown, "public/active/self/stage/attack/available") == 0
    assert coordinate(encoder, unknown, "public/active/self/stage/attack/value") == 0
    assert coordinate(encoder, unknown, "public/active/self/fainted/available") == 0
    assert coordinate(encoder, unknown, "public/trick_room/available") == 0
    assert all(coordinate(encoder, unknown, f"private/roster/{i}/item/known_empty") == 0 for i in range(6))
    assert all(coordinate(encoder, unknown, f"private/roster/{i}/item/available") == 0 for i in range(6))


def test_repeated_sets_and_canonical_positions_are_order_independent():
    train = record()
    encoder = fit([train])
    reordered = changed(train, lambda f: (
        f["public_battle"]["opponent_revealed_moves"]["move_ids"].reverse(),
        f["exact_legal_actions"]["action_ids"].reverse(),
        f["actor_private"]["own_roster"].reverse(),
        [row["moves"].reverse() for row in f["actor_private"]["own_roster"]],
    ), partition="validation", suffix="reordered")
    assert encode(encoder=encoder, semantic_record=reordered)["vector"] == encode(encoder=encoder, semantic_record=train)["vector"]


@pytest.mark.parametrize("label", [1, 0, -1])
def test_labels_and_partitions_remain_outside_vector(label):
    train = record()
    encoder = fit([train])
    other = changed(train, label=label, partition="test", suffix=f"label-{label}")
    a = encode(encoder=encoder, semantic_record=train)
    b = encode(encoder=encoder, semantic_record=other)
    assert a["vector"] == b["vector"]
    assert b["label"]["value"] == label and b["evaluation_partition"] == "test"
    assert "semantic_feature_fingerprint" not in encoder["feature_layout"]
    assert not any("session_id" in name or "battle_id" in name or "evidence_id" in name
                   or "target" in name or "partition" in name for name in encoder["feature_layout"])
    assert not {"model", "prediction", "loss", "scaler", "mean", "std"} & set(encoder)


def test_unavailable_rows_have_no_vector_or_vocabulary_effect():
    train = record()
    unavailable_args, _ = case(cause="forfeit_opponent")
    unavailable = semantic(**unavailable_args)
    assert unavailable["feature_availability"]["availability"] == "unavailable"
    # Detached historical row placed in the same explicit split for this contract test.
    unavailable = changed(unavailable, partition="validation", suffix="unavailable")
    same_split = _editable(unavailable)
    same_split["audit"]["evaluation_split_id"] = train["audit"]["evaluation_split_id"]
    unavailable = _freeze(same_split)
    encoder = fit([train, unavailable])
    assert encoder["encoder_id"] == fit([train])["encoder_id"]
    encoded = encode(encoder=encoder, semantic_record=unavailable)
    assert encoded["status"] == "encoded" and encoded["vector"] is None
    assert encoded["feature_availability"]["availability"] == "unavailable"
    assert encoded["label"]["availability"] == "unavailable" and "value" not in encoded["label"]


def test_duplicates_mixed_split_missing_train_and_forged_record_fail_closed():
    train = record()
    assert fit([train, train])["reason"] == "duplicate_semantic_record_id"
    different_split = _editable(changed(train, suffix="split"))
    different_split["audit"]["evaluation_split_id"] = "foreign-split"
    different_split = _freeze(different_split)
    assert fit([train, different_split])["reason"] == "mixed_evaluation_split_id"
    validation = changed(train, partition="validation")
    assert fit([validation])["reason"] == "no_usable_train_record"
    forged = _editable(train)
    forged["model_features"]["selected_action"]["move_id"] = "forged"
    assert fit([train, _freeze(forged)])["reason"] == "semantic_record_invalid"
    assert encode(encoder=fit([train]), semantic_record=_freeze(forged))["reason"] == "semantic_record_invalid"
    assert encode(encoder=fit([train]), semantic_record=different_split)["reason"] == "evaluation_split_mismatch"


def test_caller_data_unchanged_and_encoder_is_frozen():
    train = record()
    before = deepcopy(_editable(train))
    encoder = fit([train])
    encode(encoder=encoder, semantic_record=train)
    assert _editable(train) == before
    with pytest.raises(TypeError):
        encoder["feature_layout"] = ()
