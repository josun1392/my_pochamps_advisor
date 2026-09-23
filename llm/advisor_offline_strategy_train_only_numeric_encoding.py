"""Frozen train-only categorical encoding of approved semantic model inputs."""
from __future__ import annotations

import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from llm.advisor_offline_decision_point_provenance import DECISION_KINDS, _freeze, fingerprint_decision_contract_reference
from llm.advisor_offline_strategy_model_feature_semantics import (
    SCHEMA_VERSION as SEMANTIC_SCHEMA, validates_detached_semantic_feature_record,
)
from llm.advisor_session_decision_public_battle_information import CONDITIONS, STAT_STAGES, TERRAIN, WEATHER


ENCODER_SCHEMA = "offline-strategy-train-only-numeric-encoder-v1"
ENCODED_SCHEMA = "offline-strategy-numeric-feature-record-v1"
POLICY_VERSION = "train-only-fixed-layout-oov-v1"
FAMILIES = ("pokemon", "move", "item", "ability", "ruleset", "mechanics", "protocol", "format", "legal_action")
STAT_NAMES = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")
LIMITATIONS = ("numeric_scaling_not_applied_v1", "canonical_positions_are_encoding_artifacts_not_battle_authority",
               "detached_live_source_retention_not_independently_reproven")


def fit_train_only_numeric_encoder(records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> Mapping[str, Any]:
    """Fit only available train features; other partitions are never vocabulary input."""
    if not isinstance(records, (list, tuple)) or not records:
        return _failure("semantic_records_invalid")
    if any(not validates_detached_semantic_feature_record(row) for row in records):
        return _failure("semantic_record_invalid")
    ids = [row["feature_record_id"] for row in records]
    if len(ids) != len(set(ids)):
        return _failure("duplicate_semantic_record_id")
    split_ids = {row["audit"]["evaluation_split_id"] for row in records}
    if len(split_ids) != 1:
        return _failure("mixed_evaluation_split_id")
    train = [row for row in records if row["evaluation_partition"] == "train"
             and row["feature_availability"]["availability"] == "available"]
    if not train:
        return _failure("no_usable_train_record")
    vocab_sets: dict[str, set[str]] = {family: set() for family in FAMILIES}
    try:
        for row in train:
            _collect_categories(row["model_features"], vocab_sets)
        vocab = {family: tuple(sorted(vocab_sets[family])) for family in FAMILIES}
        layout = _layout(vocab)
        # A malformed train feature is not allowed to determine an encoder.
        for row in train:
            _vector(row["model_features"], vocab, layout)
    except (KeyError, TypeError, ValueError, IndexError):
        return _failure("train_feature_shape_invalid")
    identity = {"schema_version": ENCODER_SCHEMA, "policy_version": POLICY_VERSION,
                "vocabularies": vocab, "feature_layout": layout}
    return _freeze({
        "status": "fitted", "schema_version": ENCODER_SCHEMA,
        "encoder_id": "train-only-numeric-encoder:" + fingerprint_decision_contract_reference(identity),
        "encoding_policy_version": POLICY_VERSION,
        "evaluation_split_id": next(iter(split_ids)),
        "vector_dimension": len(layout), "feature_layout": layout,
        "vocabularies": vocab, "oov_representation": "reserved_per_open_category_family",
        "missing_numeric_storage": "zero_placeholder_with_separate_availability_coordinate_no_factual_zero_claim",
        "limitations": LIMITATIONS,
    })


def encode_semantic_feature_record(*, encoder: Mapping[str, Any], semantic_record: Mapping[str, Any]) -> Mapping[str, Any]:
    if not _valid_encoder(encoder):
        return _encoded_failure("encoder_invalid")
    if not validates_detached_semantic_feature_record(semantic_record):
        return _encoded_failure("semantic_record_invalid")
    if semantic_record["audit"]["evaluation_split_id"] != encoder["evaluation_split_id"]:
        return _encoded_failure("evaluation_split_mismatch")
    availability = semantic_record["feature_availability"]
    vector = None
    if availability["availability"] == "available":
        try:
            vector = _vector(semantic_record["model_features"], encoder["vocabularies"], encoder["feature_layout"])
        except (KeyError, TypeError, ValueError, IndexError):
            return _encoded_failure("semantic_feature_shape_invalid")
    identity = {"encoder_id": encoder["encoder_id"], "feature_record_id": semantic_record["feature_record_id"],
                "vector": vector}
    return _freeze({
        "status": "encoded", "schema_version": ENCODED_SCHEMA,
        "encoded_record_id": "encoded-semantic-feature:" + fingerprint_decision_contract_reference(identity),
        "encoder_id": encoder["encoder_id"],
        "source_semantic_feature_fingerprint": semantic_record["semantic_feature_fingerprint"],
        "feature_availability": availability, "vector": vector,
        "vector_dimension": encoder["vector_dimension"],
        "label": semantic_record["label"],
        "evaluation_partition": semantic_record["evaluation_partition"],
        "audit": {"semantic_feature_record_id": semantic_record["feature_record_id"],
                  "evaluation_split_id": semantic_record["audit"]["evaluation_split_id"],
                  "semantic_schema": SEMANTIC_SCHEMA, "limitations": LIMITATIONS},
    })


def _valid_encoder(value: Any) -> bool:
    if (not isinstance(value, MappingProxyType) or set(value) != {
        "status", "schema_version", "encoder_id", "encoding_policy_version", "evaluation_split_id", "vector_dimension",
        "feature_layout", "vocabularies", "oov_representation", "missing_numeric_storage", "limitations",
    } or value["status"] != "fitted" or value["schema_version"] != ENCODER_SCHEMA
            or value["encoding_policy_version"] != POLICY_VERSION or value["limitations"] != LIMITATIONS
            or not isinstance(value["evaluation_split_id"], str) or not value["evaluation_split_id"]
            or value["oov_representation"] != "reserved_per_open_category_family"
            or value["missing_numeric_storage"] != "zero_placeholder_with_separate_availability_coordinate_no_factual_zero_claim"):
        return False
    vocab = value["vocabularies"]
    if not isinstance(vocab, MappingProxyType) or set(vocab) != set(FAMILIES):
        return False
    for family in FAMILIES:
        tokens = vocab[family]
        if (not isinstance(tokens, tuple)
                or any(not isinstance(token, str) or not token for token in tokens)
                or tokens != tuple(sorted(set(tokens)))):
            return False
    layout = _layout(vocab)
    identity = {"schema_version": ENCODER_SCHEMA, "policy_version": POLICY_VERSION,
                "vocabularies": vocab, "feature_layout": layout}
    return (value["feature_layout"] == layout and value["vector_dimension"] == len(layout)
            and value["encoder_id"] == "train-only-numeric-encoder:" + fingerprint_decision_contract_reference(identity))


def _collect_categories(features: Mapping[str, Any], output: dict[str, set[str]]) -> None:
    rules = features["rules_and_decision"]
    for field, family in (("ruleset_id", "ruleset"), ("mechanics_version", "mechanics"),
                          ("protocol_version", "protocol"), ("battle_format_id", "format")):
        output[family].add(_token(rules[field]))
    public = features["public_battle"]
    for side in ("self", "opponent"):
        output["pokemon"].add(_token(public["active"][side]["pokemon_id"]))
    for move in public["opponent_revealed_moves"]["move_ids"]:
        output["move"].add(_token(move))
    for row in features["actor_private"]["own_roster"]:
        output["pokemon"].add(_token(row["pokemon_id"]))
        for move in row["moves"]:
            output["move"].add(_token(move["move_id"]["value"]))
        for key, family in (("known_item", "item"), ("current_ability", "ability")):
            entry = row[key]
            if entry["availability"] == "available" and entry["value"] is not None:
                output[family].add(_token(entry["value"]))
    for action in features["exact_legal_actions"]["action_ids"]:
        output["legal_action"].add(_token(action))
    selected = features["selected_action"]
    output["move" if selected["kind"] == "attack" else "pokemon"].add(
        _token(selected["move_id"] if selected["kind"] == "attack" else selected["incoming_pokemon_id"]))


def _layout(vocab: Mapping[str, tuple[str, ...]]) -> tuple[str, ...]:
    names: list[str] = []
    def cat(path: str, family: str, *, optional: bool = False, empty: bool = False) -> None:
        if optional:
            names.append(path + "/available")
        if empty:
            names.append(path + "/known_empty")
        names.append(path + "/oov")
        names.extend(path + "/cat/" + json.dumps(token, ensure_ascii=True) for token in vocab[family])
    def enum(path: str, values: Any, *, optional: bool = False) -> None:
        if optional:
            names.append(path + "/available")
        names.extend(path + "/enum/" + token for token in sorted(values))
    def number(path: str, *, optional: bool = True) -> None:
        if optional:
            names.append(path + "/available")
        names.append(path + "/value")
    for field, family in (("ruleset_id", "ruleset"), ("mechanics_version", "mechanics"),
                          ("protocol_version", "protocol"), ("battle_format_id", "format")):
        cat("rules/" + field, family)
    enum("decision/kind", DECISION_KINDS)
    number("decision/turn", optional=False)
    for side in ("self", "opponent"):
        base = "public/active/" + side
        cat(base + "/pokemon", "pokemon")
        for field in ("current_hp", "max_hp", "fainted"):
            number(base + "/" + field)
        enum(base + "/condition", CONDITIONS, optional=True)
        for stage in STAT_STAGES:
            number(base + "/stage/" + stage)
    enum("public/weather", WEATHER, optional=True)
    enum("public/terrain", TERRAIN, optional=True)
    number("public/trick_room")
    for side in ("self", "opponent"):
        number("public/tailwind/" + side)
    enum("public/revealed_scope", ("exact", "partial", "unknown"))
    cat("public/revealed_moves", "move")
    enum("private/roster_scope", ("exact", "partial", "unknown"))
    for i in range(6):
        base = f"private/roster/{i}"
        names.append(base + "/present")
        cat(base + "/pokemon", "pokemon")
        enum(base + "/move_scope", ("exact", "partial", "unknown"))
        for j in range(4):
            move_base = f"{base}/move/{j}"
            names.append(move_base + "/present")
            cat(move_base + "/id", "move", optional=True)
            number(move_base + "/pp")
        cat(base + "/item", "item", optional=True, empty=True)
        cat(base + "/ability", "ability", optional=True)
        number(base + "/level")
        for stat in STAT_NAMES:
            number(base + "/stat/" + stat)
    cat("legal/actions", "legal_action")
    enum("selected/kind", ("attack", "switch"))
    cat("selected/attack_move", "move")
    cat("selected/switch_pokemon", "pokemon")
    return tuple(names)


def _vector(features: Mapping[str, Any], vocab: Mapping[str, tuple[str, ...]], layout: tuple[str, ...]) -> tuple[int, ...]:
    values: dict[str, int] = {}
    def number(path: str, entry: Any, *, optional: bool = True) -> None:
        if optional:
            if not isinstance(entry, Mapping) or entry["availability"] not in {"available", "unavailable"}:
                raise ValueError("availability_invalid")
            if entry["availability"] == "unavailable":
                if "value" in entry:
                    raise ValueError("unavailable_value")
                return
            values[path + "/available"] = 1
            entry = entry["value"]
        boolean = path.endswith(("/fainted", "/trick_room")) or path.startswith("public/tailwind/")
        if boolean:
            if type(entry) is not bool:
                raise ValueError("boolean_invalid")
            entry = int(entry)
        elif type(entry) is not int:
            raise ValueError("numeric_invalid")
        if (not boolean and (
            (path == "decision/turn" and entry < 1)
            or (path.endswith("/current_hp") and entry < 0)
            or (path.endswith("/max_hp") and entry < 1)
            or ("/stage/" in path and not -6 <= entry <= 6)
            or (path.endswith("/pp") and entry < 0)
            or (path.endswith("/level") and not 1 <= entry <= 100)
            or ("/stat/" in path and entry < 1)
        )):
            raise ValueError("numeric_range_invalid")
        values[path + "/value"] = entry
    def cat(path: str, family: str, token: Any, *, optional: bool = False, empty: bool = False) -> None:
        if optional:
            if not isinstance(token, Mapping) or token["availability"] not in {"available", "unavailable"}:
                raise ValueError("availability_invalid")
            if token["availability"] == "unavailable":
                if "value" in token:
                    raise ValueError("unavailable_value")
                return
            values[path + "/available"] = 1
            token = token["value"]
        if empty and token is None:
            values[path + "/known_empty"] = 1
            return
        token = _token(token)
        values[path + ("/cat/" + json.dumps(token, ensure_ascii=True) if token in vocab[family] else "/oov")] = 1
    def enum(path: str, token: Any, allowed: Any, *, optional: bool = False) -> None:
        if optional:
            if not isinstance(token, Mapping) or token["availability"] not in {"available", "unavailable"}:
                raise ValueError("availability_invalid")
            if token["availability"] == "unavailable":
                if "value" in token:
                    raise ValueError("unavailable_value")
                return
            values[path + "/available"] = 1
            token = token["value"]
        if not isinstance(token, str) or token not in allowed:
            raise ValueError("enum_invalid")
        values[path + "/enum/" + token] = 1
    rules = features["rules_and_decision"]
    for field, family in (("ruleset_id", "ruleset"), ("mechanics_version", "mechanics"),
                          ("protocol_version", "protocol"), ("battle_format_id", "format")):
        cat("rules/" + field, family, rules[field])
    enum("decision/kind", rules["decision_kind"], DECISION_KINDS)
    number("decision/turn", rules["turn_number"], optional=False)
    public = features["public_battle"]
    for side in ("self", "opponent"):
        row = public["active"][side]
        if (row["current_hp"]["availability"] == "available" and row["max_hp"]["availability"] == "available"
                and row["current_hp"]["value"] > row["max_hp"]["value"]):
            raise ValueError("hp_inconsistent")
        base = "public/active/" + side
        cat(base + "/pokemon", "pokemon", row["pokemon_id"])
        for field in ("current_hp", "max_hp", "fainted"):
            number(base + "/" + field, row[field])
        enum(base + "/condition", row["condition"], CONDITIONS, optional=True)
        for stage in STAT_STAGES:
            number(base + "/stage/" + stage, row["stat_stages"][stage])
    enum("public/weather", public["field"]["weather"], WEATHER, optional=True)
    enum("public/terrain", public["field"]["terrain"], TERRAIN, optional=True)
    number("public/trick_room", public["field"]["trick_room"])
    for side in ("self", "opponent"):
        number("public/tailwind/" + side, public["sides"][side]["tailwind"])
    revealed = public["opponent_revealed_moves"]
    if revealed["status"] == "unknown" and revealed["move_ids"]:
        raise ValueError("revealed_moves_inconsistent")
    enum("public/revealed_scope", revealed["status"], ("exact", "partial", "unknown"))
    for move in revealed["move_ids"]:
        cat("public/revealed_moves", "move", move)
    own = features["actor_private"]
    enum("private/roster_scope", own["roster_scope"]["status"], ("exact", "partial", "unknown"))
    rows = sorted(own["own_roster"], key=fingerprint_decision_contract_reference)
    if len(rows) > 6:
        raise ValueError("roster_too_large")
    for i, row in enumerate(rows):
        base = f"private/roster/{i}"
        values[base + "/present"] = 1
        cat(base + "/pokemon", "pokemon", row["pokemon_id"])
        enum(base + "/move_scope", row["move_scope"]["status"], ("exact", "partial", "unknown"))
        moves = sorted(row["moves"], key=fingerprint_decision_contract_reference)
        if len(moves) > 4:
            raise ValueError("moves_too_many")
        for j, move in enumerate(moves):
            move_base = f"{base}/move/{j}"
            values[move_base + "/present"] = 1
            cat(move_base + "/id", "move", move["move_id"], optional=True)
            number(move_base + "/pp", move["current_pp"])
        cat(base + "/item", "item", row["known_item"], optional=True, empty=True)
        cat(base + "/ability", "ability", row["current_ability"], optional=True)
        number(base + "/level", row["current_level"])
        for stat in STAT_NAMES:
            number(base + "/stat/" + stat, row["current_final_stats"][stat])
    legal = features["exact_legal_actions"]
    if legal["status"] != "exact":
        raise ValueError("legal_not_exact")
    for action in legal["action_ids"]:
        cat("legal/actions", "legal_action", action)
    selected = features["selected_action"]
    enum("selected/kind", selected["kind"], ("attack", "switch"))
    if selected["kind"] == "attack":
        cat("selected/attack_move", "move", selected["move_id"])
    else:
        cat("selected/switch_pokemon", "pokemon", selected["incoming_pokemon_id"])
    if any(name not in layout for name in values):
        raise ValueError("layout_coordinate_invalid")
    return tuple(values.get(name, 0) for name in layout)


def _token(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("token_invalid")
    return value


def _failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": ENCODER_SCHEMA, "reason": reason})


def _encoded_failure(reason: str) -> Mapping[str, Any]:
    return MappingProxyType({"status": "rejected", "schema_version": ENCODED_SCHEMA, "reason": reason})
