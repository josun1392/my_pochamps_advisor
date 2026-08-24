"""Detached, partial current stat-stage authority adapters."""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping

STAGE_KEYS = ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")
NATIVE_DAMAGE_STAGE_KEYS = STAGE_KEYS[:5]
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")

def project_current_stage_authority(*, session_id: str, source_runtime_fingerprint: str, source_branch_fingerprint: str, owner: Mapping[str, Any], current_stages: Any) -> dict[str, Any]:
    """Project reducer stages; omission is unknown, never a neutral default."""
    if not _binding(session_id, source_runtime_fingerprint, source_branch_fingerprint, owner): return {"status":"rejected","reason":"invalid_current_stage_authority_binding"}
    values = current_stages if isinstance(current_stages, Mapping) else {}
    stages = {stat: ({"status":"known","value":value,"provenance":"runtime_battle_state_v1"} if _stage(value) else {"status":"unknown","reason":"runtime_stat_stage_unknown"}) for stat in STAGE_KEYS for value in (values.get(stat),)}
    return {"status":"resolved","schema_version":"runtime-current-stage-authority-v1","session_id":session_id,"source_runtime_fingerprint":source_runtime_fingerprint,"source_branch_fingerprint":source_branch_fingerprint,"owner":deepcopy(dict(owner)),"stages":stages,"provenance":"runtime_battle_state_v1_current_stage_projection_v1"}

def native_damage_stage_authority(authority: Mapping[str, Any]) -> dict[str, Any]:
    """Select only the native damage five-stage contract."""
    if not _authority(authority): return {"status":"rejected","reason":"invalid_current_stage_authority"}
    missing = [stat for stat in NATIVE_DAMAGE_STAGE_KEYS if authority["stages"].get(stat, {}).get("status") != "known"]
    return {"status":"incomplete","missing_stages":missing} if missing else {"status":"resolved","stages":{stat:authority["stages"][stat]["value"] for stat in NATIVE_DAMAGE_STAGE_KEYS}}

def strict_hit_stage_authority(*, attacker_authority: Mapping[str, Any], target_authority: Mapping[str, Any]) -> dict[str, Any]:
    """Produce legacy hit-helper input only when Accuracy and Evasion are exact."""
    if not _authority(attacker_authority) or not _authority(target_authority): return {"status":"rejected","reason":"invalid_current_stage_authority"}
    if not _same_binding(attacker_authority, target_authority): return {"status":"rejected","reason":"current_stage_authority_binding_mismatch"}
    missing = []
    if attacker_authority["stages"]["accuracy"]["status"] != "known": missing.append("attacker_accuracy_stage")
    if target_authority["stages"]["evasion"]["status"] != "known": missing.append("target_evasion_stage")
    if missing: return {"status":"incomplete","missing_authority":missing,"reason":missing[0]}
    return {"status":"resolved","schema_version":"strict-hit-stage-authority-v1","session_id":attacker_authority["session_id"],"source_runtime_fingerprint":attacker_authority["source_runtime_fingerprint"],"source_branch_fingerprint":attacker_authority["source_branch_fingerprint"],"attacker":deepcopy(attacker_authority["owner"]),"target":deepcopy(target_authority["owner"]),"stat_stage_context":{"current_stages":[{"side":"self","stat":"accuracy","stage":attacker_authority["stages"]["accuracy"]["value"],"status":"user_confirmed","source":"user_confirmed_current_stat_stage","confidence":"known"},{"side":"opponent","stat":"evasion","stage":target_authority["stages"]["evasion"]["value"],"status":"user_confirmed","source":"user_confirmed_current_stat_stage","confidence":"known"}]},"provenance":"runtime_current_stage_authority_v1_strict_hit_adapter_v1"}

def _stage(value: Any) -> bool: return isinstance(value, int) and not isinstance(value, bool) and -6 <= value <= 6
def _binding(session: Any, runtime: Any, branch: Any, owner: Any) -> bool:
    return isinstance(session,str) and bool(session) and isinstance(runtime,str) and bool(runtime) and isinstance(branch,str) and bool(branch) and isinstance(owner,Mapping) and set(owner)==set(_OWNER_KEYS) and owner.get("session_id")==session and owner.get("side") in {"self","opponent"} and isinstance(owner.get("slot_index"),int) and not isinstance(owner.get("slot_index"),bool) and owner["slot_index"]>=0 and isinstance(owner.get("pokemon_id"),str) and bool(owner["pokemon_id"])
def _authority(value: Any) -> bool:
    return isinstance(value,Mapping) and value.get("status")=="resolved" and value.get("schema_version")=="runtime-current-stage-authority-v1" and _binding(value.get("session_id"),value.get("source_runtime_fingerprint"),value.get("source_branch_fingerprint"),value.get("owner")) and isinstance(value.get("stages"),Mapping) and set(value["stages"])==set(STAGE_KEYS)
def _same_binding(left: Mapping[str,Any], right: Mapping[str,Any]) -> bool:
    return all(left.get(key)==right.get(key) for key in ("session_id","source_runtime_fingerprint","source_branch_fingerprint")) and left["owner"].get("side") != right["owner"].get("side")
