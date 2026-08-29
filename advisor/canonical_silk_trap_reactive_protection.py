"""Canonical Silk Trap metadata; no protection or stage mechanics live here."""
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

_PATH=Path(__file__).parents[1]/"data"/"static"/"contact_reactive_protection_move_effects.json"
def canonical_contact_reactive_protection_metadata(move_id: Any)->dict[str,Any]|None:
 if move_id not in {"silk-trap","kings-shield"}: return None
 try: data=json.loads(_PATH.read_text(encoding="utf-8")); row=data.get("moves",{}).get(move_id)
 except (OSError,json.JSONDecodeError): return None
 expected={"silk-trap":{"owner":"blocked_attacker","stat":"speed","delta":-1},"kings-shield":{"owner":"blocked_attacker","stat":"attack","delta":-1}}[move_id]
 if not isinstance(row,Mapping) or row.get("protects_self") is not True or row.get("blocks_supported_direct_damage") is not True or row.get("protection_kind")!="ordinary_self_protection" or row.get("reactive_contact_effect")!=expected: return None
 return {"move_id":move_id,**deepcopy(dict(row))}
def canonical_silk_trap_metadata(move_id: Any)->dict[str,Any]|None:
 return canonical_contact_reactive_protection_metadata(move_id) if move_id=="silk-trap" else None

def canonical_kings_shield_metadata(move_id: Any)->dict[str,Any]|None:
 return canonical_contact_reactive_protection_metadata(move_id) if move_id=="kings-shield" else None
