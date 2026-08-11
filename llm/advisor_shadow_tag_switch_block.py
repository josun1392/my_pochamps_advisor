"""Post-freeze, block-only Shadow Tag authority and switch-legality finalizer."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping, Sequence


def derive_shadow_tag_block(*, authority: Mapping[str, Any], self_type: Mapping[str, Any], self_item: Mapping[str, Any], self_ability: Mapping[str, Any]) -> dict[str, Any]:
    """Never infer permission; prove a block only from complete frozen inputs."""
    base = {"mechanic": "shadow_tag", "session_id": authority.get("session_id") if isinstance(authority, Mapping) else None, "source": deepcopy(authority.get("source")) if isinstance(authority, Mapping) else None, "target": deepcopy(authority.get("target")) if isinstance(authority, Mapping) else None}
    if not isinstance(authority, Mapping) or authority.get("ability_id") != "shadow-tag": return {**base, "state": "not_established"}
    if authority.get("applicability") != "applicable" or authority.get("interaction") != "affecting": return {**base, "state": "insufficient_context"}
    types = self_type.get("types") if isinstance(self_type, Mapping) and self_type.get("status") == "known" else None
    item = self_item.get("value") if isinstance(self_item, Mapping) and self_item.get("status") in {"known", "known_absent"} else None
    ability = self_ability.get("value") if isinstance(self_ability, Mapping) and self_ability.get("status") == "known" else None
    if not isinstance(types, Sequence) or isinstance(types, (str, bytes)) or not isinstance(self_item, Mapping) or self_item.get("status") not in {"known", "known_absent"} or not isinstance(self_ability, Mapping) or self_ability.get("status") != "known": return {**base, "state": "insufficient_context"}
    if "ghost" in types or item == "shed-shell" or ability == "shadow-tag": return {**base, "state": "exception_applies"}
    return {**base, "state": "confirmed_blocked"}


def resolve_effective_switch_permission(manual: Mapping[str, Any], blocker: Mapping[str, Any]) -> dict[str, str]:
    """Central manual-plus-hard-block precedence; mechanics never grant permission."""
    manual_status = manual.get("status") if isinstance(manual, Mapping) else "unknown"
    if manual_status == "blocked" or (isinstance(blocker, Mapping) and blocker.get("state") == "confirmed_blocked"): return {"status": "blocked"}
    if manual_status == "permitted": return {"status": "permitted"}
    return {"status": "unknown"}


def finalize_switch_candidates(base_candidates: Sequence[Mapping[str, Any]], *, manual_permission: Mapping[str, Any], blocker: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Detach post-freeze legality without changing identity/availability authority."""
    effective = resolve_effective_switch_permission(manual_permission, blocker)
    out=[]
    for candidate in base_candidates:
        row=deepcopy(dict(candidate)); available=row.get("availability_supportability") == "complete" and row.get("reason_code") not in {"target_fainted", "target_availability_unknown"}
        if available and effective["status"] == "permitted": row.update({"selectable":True,"legality_supportability":"complete","reason_code":"switch_available"})
        elif effective["status"] == "blocked": row.update({"selectable":False,"legality_supportability":"complete","reason_code":"switch_blocked"})
        else: row.update({"selectable":False,"legality_supportability":"insufficient_context","reason_code":"switch_legality_unknown"})
        out.append(row)
    return out
