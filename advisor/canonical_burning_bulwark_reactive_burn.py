"""Maintained canonical metadata for Burning Bulwark's blocked-contact burn."""
from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

_PATH=Path(__file__).parents[1]/"data"/"static"/"burning_bulwark_reactive_burn_effects.json"
_EFFECT={"owner":"blocked_attacker","condition_before":"none","condition_after":"burn","trigger":"burning_bulwark_successful_blocked_contact"}
def canonical_burning_bulwark_reactive_burn_metadata(move_id: Any)->dict[str,Any]|None:
 if move_id!="burning-bulwark":return None
 try: row=json.loads(_PATH.read_text(encoding="utf-8")).get("moves",{}).get(move_id)
 except (OSError,json.JSONDecodeError):return None
 if not isinstance(row,Mapping) or row.get("protects_self") is not True or row.get("blocks_supported_direct_damage") is not True or row.get("reactive_contact_condition")!=_EFFECT:return None
 return {"move_id":move_id,**deepcopy(dict(row))}
