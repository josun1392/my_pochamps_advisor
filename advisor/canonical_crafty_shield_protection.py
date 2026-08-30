"""Maintained canonical Crafty Shield applicability metadata."""
from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping
_PATH=Path(__file__).parents[1]/"data"/"static"/"crafty_shield_protection_effects.json"
_RULE={"protects_side":True,"protection_kind":"status_action_guard","blocks_supported_pure_status_actions":True,"target_requirement":"protected_recipient"}
def canonical_crafty_shield_protection_metadata(move_id: Any)->dict[str,Any]|None:
 if move_id!="crafty-shield": return None
 try: row=json.loads(_PATH.read_text(encoding="utf-8")).get("moves",{}).get(move_id)
 except (OSError,json.JSONDecodeError): return None
 if not isinstance(row,Mapping) or any(row.get(k)!=v for k,v in _RULE.items()): return None
 return {"move_id":move_id,**deepcopy(dict(row))}
