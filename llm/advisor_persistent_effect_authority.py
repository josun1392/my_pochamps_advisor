"""Bounded branch-wide authority for supported persistent effects only."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

_FAMILIES = ("aqua_ring", "ingrain", "leech_seed")
_PROVENANCE = "trusted_branch_persistent_effect_materialization"

def materialize_persistent_effect_authority(*, owners: Mapping[str, Mapping[str, Any]], source_branch_fingerprint: str, states: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None) -> dict[str, Any]:
    """Purely materialize affirmative state; absent input is explicitly unknown."""
    rows=[]
    for side, owner in owners.items():
        for family in _FAMILIES:
            supplied = states.get(side, {}).get(family) if isinstance(states, Mapping) and isinstance(states.get(side), Mapping) else None
            status = supplied.get("state") if isinstance(supplied, Mapping) else "unknown"
            row={"family":family,"owner":deepcopy(dict(owner)),"state":status,"provenance":supplied.get("provenance", _PROVENANCE) if isinstance(supplied, Mapping) else _PROVENANCE}
            if family == "leech_seed" and status == "known_active" and isinstance(supplied.get("source_slot"), Mapping): row["source_slot"] = deepcopy(dict(supplied["source_slot"]))
            rows.append(row)
    return {"schema_version":"branch-persistent-effect-authority-v1","session_id":next(iter(owners.values()))["session_id"],"source_branch_fingerprint":source_branch_fingerprint,"provenance":_PROVENANCE,"states":rows}

def persistent_effect_state(state: Mapping[str, Any], family: str, side: str, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    bundle=state.get("branch_persistent_effect_authority")
    if not isinstance(bundle, Mapping) or bundle.get("schema_version")!="branch-persistent-effect-authority-v1" or bundle.get("session_id")!=owner.get("session_id") or not isinstance(bundle.get("source_branch_fingerprint"),str) or bundle.get("provenance")!=_PROVENANCE:return None
    rows=bundle.get("states"); matches=[row for row in rows if isinstance(row,Mapping) and row.get("family")==family and row.get("owner")==dict(owner)] if isinstance(rows,list) else []
    if len(matches)!=1 or matches[0].get("state") not in {"known_active","known_inactive","unknown"}:return None
    return matches[0]
