"""Pinned canonical lifecycle taxonomy for the bounded charge-move inventory."""
from __future__ import annotations

import hashlib
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "canonical-charge-move-lifecycle-v1"
INVENTORY_SCHEMA_VERSION = "canonical-charge-move-lifecycle-inventory-v1"
COMMIT = "6b4bc34e44cc2541929cc4b8fff96e756ab3f268"
EXPECTED_MOVES_SHA256 = "1ded02b7fda2e4cfcc28ad753190f83c3db3ac5947d2825c2663e66d8ce83d6b"
EXPECTED_ITEMS_SHA256 = "b8ec6ef48590402e83502902f5205a798c02a72f35d710d35cd30902e08c3f4e"

_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "data" / "vendor" / "pokemon_showdown" / COMMIT
_MOVES_PATH = _VENDOR / "moves.ts"
_ITEMS_PATH = _VENDOR / "items.ts"

_COMMON_MOVE_TOKENS = (
    "charge: 1",
    "if (attacker.removeVolatile(move.id))",
    "this.runEvent('ChargeMove', attacker, defender, move)",
    "attacker.addVolatile('twoturnmove', defender)",
)

_ROWS: dict[str, dict[str, Any]] = {
    "meteor-beam": {
        "showdown_id": "meteorbeam",
        "lifecycle_family": "charge_turn_self_effect_then_damage",
        "execution_model": "charge_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "special_attack_plus_one",
        "charge_turn_side_effect_timing": "before_charge_move_event",
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("this.boost({ spa: 1 }, attacker, attacker, move);",),
    },
    "sky-attack": {
        "showdown_id": "skyattack",
        "lifecycle_family": "ordinary_charge_then_damage",
        "execution_model": "charge_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("accuracy: 90", "basePower: 140", "category: \"Physical\"", "type: \"Flying\"", "critRatio: 2", "chance: 30", "volatileStatus: 'flinch'"),
    },
    "solar-beam": {
        "showdown_id": "solarbeam",
        "lifecycle_family": "weather_sensitive_charge_then_damage",
        "execution_model": "charge_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": True,
        "weak_weather_damage_modifier_present": True,
        "tokens": (
            "['sunnyday', 'desolateland'].includes(attacker.effectiveWeather(undefined, true))",
            "const weakWeathers = ['raindance', 'primordialsea', 'sandstorm', 'hail', 'snowscape'];",
            "return this.chainModify(0.5);",
        ),
    },
    "solar-blade": {
        "showdown_id": "solarblade",
        "lifecycle_family": "weather_sensitive_charge_then_damage",
        "execution_model": "charge_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": True,
        "weak_weather_damage_modifier_present": True,
        "tokens": (
            "['sunnyday', 'desolateland'].includes(attacker.effectiveWeather(undefined, true))",
            "const weakWeathers = ['raindance', 'primordialsea', 'sandstorm', 'hail', 'snowscape'];",
            "return this.chainModify(0.5);",
        ),
    },
    "fly": {
        "showdown_id": "fly",
        "lifecycle_family": "semi_invulnerable_charge_then_damage",
        "execution_model": "semi_invulnerable_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": "airborne",
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("condition: {", "onInvulnerability(target, source, move)", "move.id === 'gust' || move.id === 'twister'"),
    },
    "dig": {
        "showdown_id": "dig",
        "lifecycle_family": "semi_invulnerable_charge_then_damage",
        "execution_model": "semi_invulnerable_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": "underground",
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("condition: {", "onInvulnerability(target, source, move)", "move.id === 'earthquake' || move.id === 'magnitude'"),
    },
    "dive": {
        "showdown_id": "dive",
        "lifecycle_family": "semi_invulnerable_charge_then_damage",
        "execution_model": "semi_invulnerable_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": "underwater",
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("condition: {", "onInvulnerability(target, source, move)", "move.id === 'surf' || move.id === 'whirlpool'"),
    },
    "bounce": {
        "showdown_id": "bounce",
        "lifecycle_family": "semi_invulnerable_charge_then_damage",
        "execution_model": "semi_invulnerable_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": "airborne",
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("condition: {", "onInvulnerability(target, source, move)", "move.id === 'gust' || move.id === 'twister'"),
    },
    "phantom-force": {
        "showdown_id": "phantomforce",
        "lifecycle_family": "semi_invulnerable_charge_then_damage",
        "execution_model": "semi_invulnerable_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": "vanished",
        "protection_bypass_later_execution": True,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("breaksProtect: true", "condition: {", "onInvulnerability: false"),
    },
    "shadow-force": {
        "showdown_id": "shadowforce",
        "lifecycle_family": "semi_invulnerable_charge_then_damage",
        "execution_model": "semi_invulnerable_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": "vanished",
        "protection_bypass_later_execution": True,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("breaksProtect: true", "condition: {", "onInvulnerability: false"),
    },
    "skull-bash": {
        "showdown_id": "skullbash",
        "lifecycle_family": "charge_turn_self_effect_then_damage",
        "execution_model": "charge_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "defense_plus_one",
        "charge_turn_side_effect_timing": "before_charge_move_event",
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("this.boost({ def: 1 }, attacker, attacker, move);",),
    },
    "razor-wind": {
        "showdown_id": "razorwind",
        "lifecycle_family": "ordinary_charge_then_damage",
        "execution_model": "charge_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("accuracy: 100", "basePower: 80", "category: \"Special\"", "type: \"Normal\"", "critRatio: 2"),
    },
    "freeze-shock": {
        "showdown_id": "freezeshock",
        "lifecycle_family": "ordinary_charge_then_damage",
        "execution_model": "charge_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("accuracy: 90", "basePower: 140", "category: \"Physical\"", "type: \"Ice\"", "chance: 30", "status: 'par'"),
    },
    "ice-burn": {
        "showdown_id": "iceburn",
        "lifecycle_family": "ordinary_charge_then_damage",
        "execution_model": "charge_then_execute",
        "terminal_effect_class": "damaging_move",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("accuracy: 90", "basePower: 140", "category: \"Special\"", "type: \"Ice\"", "chance: 30", "status: 'brn'"),
    },
    "geomancy": {
        "showdown_id": "geomancy",
        "lifecycle_family": "charge_then_status_terminal",
        "execution_model": "other_two_turn",
        "terminal_effect_class": "self_stat_change",
        "charge_turn_side_effect_class": "none",
        "charge_turn_side_effect_timing": None,
        "semi_invulnerability_class": None,
        "protection_bypass_later_execution": False,
        "weather_sensitive_charge_skip": False,
        "weak_weather_damage_modifier_present": False,
        "tokens": ("category: \"Status\"", "basePower: 0", "boosts: {", "spa: 2", "spd: 2", "spe: 2"),
    },
}


def normalize_charge_move_id(move_id: str) -> str:
    return move_id.strip().lower().replace("_", "-").replace(" ", "-")


def resolve_canonical_charge_move_lifecycle(move_id: Any) -> dict[str, Any]:
    if not isinstance(move_id, str) or not move_id.strip():
        return {"status": "incomplete", "schema_version": SCHEMA_VERSION, "reason": "charge_move_identity_unknown"}
    normalized = normalize_charge_move_id(move_id)
    row = _ROWS.get(normalized)
    if row is None:
        return {
            "status": "not_applicable",
            "schema_version": SCHEMA_VERSION,
            "move_id": normalized,
            "reason": "move_not_in_bounded_charge_inventory",
        }
    source, error = _authenticated_source()
    if error is not None:
        return {
            "status": "rejected",
            "schema_version": SCHEMA_VERSION,
            "move_id": normalized,
            "reason": error,
        }
    move_proof = source["move_proofs"].get(normalized)
    if not isinstance(move_proof, dict):
        return {
            "status": "rejected",
            "schema_version": SCHEMA_VERSION,
            "move_id": normalized,
            "reason": "canonical_charge_move_source_proof_missing",
        }
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        "move_id": normalized,
        "showdown_move_id": row["showdown_id"],
        "is_charge_move": True,
        "charge_flag_confirmed": True,
        "charge_type": (
            "semi_invulnerable"
            if row["execution_model"] == "semi_invulnerable_then_execute"
            else "other_two_turn"
            if row["execution_model"] == "other_two_turn"
            else "standard_charge"
        ),
        "lifecycle_family": row["lifecycle_family"],
        "execution_model": row["execution_model"],
        "charge_move_event_participation": True,
        "twoturnmove_state_usage": True,
        "existing_move_volatile_continuation": True,
        "terminal_effect_class": row["terminal_effect_class"],
        "power_herb_eligible": True,
        "power_herb_charge_skip_possible": True,
        "power_herb_behavior": "descriptive_skip_mechanism_only",
        "weather_sensitive_charge_skip": row["weather_sensitive_charge_skip"],
        "sunny_weather_skip_sources": (
            ("sunnyday", "desolateland") if row["weather_sensitive_charge_skip"] else ()
        ),
        "weak_weather_damage_modifier_present": row["weak_weather_damage_modifier_present"],
        "charge_turn_side_effect_class": row["charge_turn_side_effect_class"],
        "charge_turn_side_effect_timing": row["charge_turn_side_effect_timing"],
        "semi_invulnerability_class": row["semi_invulnerability_class"],
        "semi_invulnerability_special_interactions_present": row["semi_invulnerability_class"] is not None,
        "protection_bypass_later_execution": row["protection_bypass_later_execution"],
        "canonical_recognition_grants_immediate_execution": False,
        "source": "pinned_showdown_charge_move_lifecycle_v1",
        "confidence": "authenticated_pinned_source",
        "notes": "Canonical recognition only; runtime charge/execute lifecycle remains unrepresented.",
        "source_provenance": {
            "repository": "https://github.com/smogon/pokemon-showdown",
            "commit_sha": COMMIT,
            "moves_source_path": "data/moves.ts",
            "moves_sha256": source["moves_sha256"],
            "items_source_path": "data/items.ts",
            "items_sha256": source["items_sha256"],
            "move_block": deepcopy(move_proof),
            "power_herb_block": deepcopy(source["power_herb_proof"]),
        },
        "provenance": "authenticated_canonical_charge_move_lifecycle_v1",
    }


def load_canonical_charge_move_lifecycle_inventory() -> dict[str, Any]:
    source, error = _authenticated_source()
    if error is not None:
        raise ValueError(error)
    moves: dict[str, dict[str, Any]] = {}
    for move_id in _ROWS:
        resolved = resolve_canonical_charge_move_lifecycle(move_id)
        if resolved.get("status") != "resolved":
            raise ValueError(resolved.get("reason", "canonical_charge_move_inventory_unavailable"))
        moves[move_id] = {key: deepcopy(value) for key, value in resolved.items() if key != "status"}
    if len(moves) != 15 or len(set(moves)) != 15:
        raise ValueError("canonical_charge_move_inventory_cardinality_invalid")
    return {
        "version": INVENTORY_SCHEMA_VERSION,
        "moves": moves,
        "source_provenance": {
            "repository": "https://github.com/smogon/pokemon-showdown",
            "commit_sha": COMMIT,
            "moves_sha256": source["moves_sha256"],
            "items_sha256": source["items_sha256"],
        },
    }


@lru_cache(maxsize=1)
def _authenticated_source() -> tuple[dict[str, Any] | None, str | None]:
    taxonomy_error = _validate_taxonomy_rows()
    if taxonomy_error is not None:
        return None, taxonomy_error
    try:
        moves_bytes = _MOVES_PATH.read_bytes()
        items_bytes = _ITEMS_PATH.read_bytes()
    except OSError:
        return None, "canonical_charge_move_pinned_source_missing"
    moves_hash = hashlib.sha256(moves_bytes).hexdigest()
    items_hash = hashlib.sha256(items_bytes).hexdigest()
    if moves_hash != EXPECTED_MOVES_SHA256:
        return None, "canonical_charge_move_moves_source_hash_mismatch"
    if items_hash != EXPECTED_ITEMS_SHA256:
        return None, "canonical_charge_move_items_source_hash_mismatch"
    moves_text = moves_bytes.decode("utf-8")
    items_text = items_bytes.decode("utf-8")
    power_herb = _extract_object_block(items_text, "powerherb")
    if power_herb is None:
        return None, "canonical_charge_move_power_herb_block_missing"
    power_tokens = (
        "onChargeMove(pokemon, target, move)",
        "if (pokemon.useItem())",
        "return false; // skip charge turn",
    )
    if any(token not in power_herb for token in power_tokens):
        return None, "canonical_charge_move_power_herb_contract_mismatch"
    proofs: dict[str, dict[str, Any]] = {}
    seen_showdown_ids: set[str] = set()
    for move_id, row in _ROWS.items():
        showdown_id = row["showdown_id"]
        if showdown_id in seen_showdown_ids:
            return None, "canonical_charge_move_duplicate_showdown_id"
        seen_showdown_ids.add(showdown_id)
        block = _extract_object_block(moves_text, showdown_id)
        if block is None:
            return None, f"canonical_charge_move_block_missing:{move_id}"
        required = _COMMON_MOVE_TOKENS + tuple(row["tokens"])
        missing = tuple(token for token in required if token not in block)
        if missing:
            return None, f"canonical_charge_move_lifecycle_token_mismatch:{move_id}"
        proofs[move_id] = {
            "showdown_move_id": showdown_id,
            "charge_flag_token": "charge: 1",
            "continuation_token": "if (attacker.removeVolatile(move.id))",
            "charge_move_event_token": "this.runEvent('ChargeMove', attacker, defender, move)",
            "twoturnmove_token": "attacker.addVolatile('twoturnmove', defender)",
            "move_specific_tokens": tuple(row["tokens"]),
        }
    return {
        "moves_sha256": moves_hash,
        "items_sha256": items_hash,
        "move_proofs": proofs,
        "power_herb_proof": {
            "showdown_item_id": "powerherb",
            "on_charge_move": True,
            "uses_item": True,
            "returns_false_to_skip_charge": True,
            "execution_grant": False,
        },
    }, None


def _validate_taxonomy_rows() -> str | None:
    if len(_ROWS) != 15 or len(set(_ROWS)) != 15:
        return "canonical_charge_move_inventory_definition_invalid"
    required = {
        "showdown_id", "lifecycle_family", "execution_model",
        "terminal_effect_class", "charge_turn_side_effect_class",
        "charge_turn_side_effect_timing", "semi_invulnerability_class",
        "protection_bypass_later_execution", "weather_sensitive_charge_skip",
        "weak_weather_damage_modifier_present", "tokens",
    }
    lifecycle_families = {
        "ordinary_charge_then_damage",
        "weather_sensitive_charge_then_damage",
        "charge_turn_self_effect_then_damage",
        "semi_invulnerable_charge_then_damage",
        "charge_then_status_terminal",
    }
    execution_models = {
        "charge_then_execute", "semi_invulnerable_then_execute", "other_two_turn",
    }
    terminal_classes = {"damaging_move", "self_stat_change"}
    for move_id, row in _ROWS.items():
        if (
            not isinstance(move_id, str) or not move_id
            or not isinstance(row, dict) or set(row) != required
            or not isinstance(row.get("showdown_id"), str) or not row["showdown_id"]
            or row.get("lifecycle_family") not in lifecycle_families
            or row.get("execution_model") not in execution_models
            or row.get("terminal_effect_class") not in terminal_classes
            or not isinstance(row.get("charge_turn_side_effect_class"), str)
            or row.get("charge_turn_side_effect_timing") not in {None, "before_charge_move_event"}
            or row.get("semi_invulnerability_class") not in {None, "airborne", "underground", "underwater", "vanished"}
            or not isinstance(row.get("protection_bypass_later_execution"), bool)
            or not isinstance(row.get("weather_sensitive_charge_skip"), bool)
            or not isinstance(row.get("weak_weather_damage_modifier_present"), bool)
            or not isinstance(row.get("tokens"), tuple)
            or any(not isinstance(token, str) or not token for token in row["tokens"])
        ):
            return f"canonical_charge_move_taxonomy_malformed:{move_id}"
    return None


def _extract_object_block(text: str, object_id: str) -> str | None:
    marker = f"\n\t{object_id}: {{"
    start = text.find(marker)
    if start < 0:
        return None
    cursor = start + len(marker)
    depth = 1
    while cursor < len(text) and depth:
        char = text[cursor]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        cursor += 1
    if depth != 0:
        return None
    return text[start:cursor]
