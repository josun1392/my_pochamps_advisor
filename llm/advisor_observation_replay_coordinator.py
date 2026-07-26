"""Private, explicit preview/apply seam for canonical observation evidence."""
from copy import deepcopy

from llm.advisor_reducer_state_model import execute_atomic_transition
from llm.advisor_replay_policy import build_replay_plan


class ObservationReplayCoordinator:
    """Process-local coordinator; callers retain explicit apply authority."""
    def __init__(self, store):
        self._store = store
        self._applied = {}

    def preview(self, observation_snapshot):
        session = observation_snapshot.get("session_id") if isinstance(observation_snapshot, dict) else None
        if not isinstance(session, str) or not session:
            return _result("session_mismatch")
        read = self._store.read_snapshot(session)
        if read.get("status") != "ready":
            return _result("session_mismatch" if read.get("status") == "session_mismatch" else read.get("status"))
        observations = deepcopy(observation_snapshot.get("ordered_observations", [])) if observation_snapshot.get("status") == "ready" else []
        ledger = self._applied.get(session, {})
        fresh, already, conflicts = [], [], []
        for event in observations if isinstance(observations, list) else []:
            if not isinstance(event, dict): continue
            oid = event.get("observation_id")
            prior = ledger.get(oid)
            if prior is None: fresh.append(event)
            elif prior == event: already.append(oid)
            else: conflicts.append({"observation_id": oid, "reason": "conflicting_applied_observation"})
        if conflicts: return _result("transition_invalid", read=read, conflicts=conflicts)
        plan = build_replay_plan(read["state"], fresh)
        if plan["status"] != "planned": return _result("transition_invalid", read=read, plan=plan, conflicts=plan.get("conflicts"))
        if not plan["ordered_steps"]:
            return _result("already_applied" if already else "no_eligible_observations", read=read, plan=plan, already=already)
        execution = execute_atomic_transition(read["state"], plan, expected_session_id=session, expected_base_fingerprint=read["state_fingerprint"])
        if execution["status"] != "committed": return _result("transition_invalid", read=read, plan=plan, execution=execution)
        return _result("preview_ready", read=read, plan=plan, execution=execution, already=already)

    def apply_confirmed_observations(self, observation_snapshot):
        preview = self.preview(observation_snapshot)
        if preview["status"] != "preview_ready": return preview
        read, execution = preview["store_snapshot"], preview["execution"]
        replaced = self._store.compare_and_replace(execution["committed_state"], expected_session_id=read["session_id"], expected_base_fingerprint=read["state_fingerprint"])
        if replaced["status"] != "replaced":
            return _result("cas_conflict" if replaced["status"] == "stale_state" else "transition_invalid", read=read, plan=preview["replay_plan"], execution=execution)
        session = read["session_id"]
        ledger = self._applied.setdefault(session, {})
        accepted = {event["observation_id"]: deepcopy(event) for event in preview["replay_plan"]["accepted_events"]}
        ledger.update(accepted)
        return _result("applied", read=read, plan=preview["replay_plan"], execution=execution, applied=execution["applied_step_ids"], state=replaced["state_snapshot"])

    def export_applied_ledger(self, session_id):
        return deepcopy(self._applied.get(session_id, {}))

    def replace_applied_ledger(self, session_id, ledger):
        if not isinstance(session_id, str) or not session_id or not isinstance(ledger, dict) or not all(isinstance(key, str) and isinstance(value, dict) for key, value in ledger.items()):
            return False
        self._applied[session_id] = deepcopy(ledger)
        return True


def _result(status, *, read=None, plan=None, execution=None, conflicts=None, already=None, applied=None, state=None):
    return {"status": status, "store_snapshot": deepcopy(read) if read else None, "replay_plan": deepcopy(plan) if plan else None, "execution": deepcopy(execution) if execution else None, "projected_state": deepcopy(execution.get("committed_state")) if isinstance(execution, dict) else None, "eligible_observations": deepcopy(plan.get("accepted_events", [])) if isinstance(plan, dict) else [], "ineligible_observations": deepcopy((plan.get("evidence_only_events", []) + plan.get("unsupported_events", []) + plan.get("excluded_events", []))) if isinstance(plan, dict) else [], "already_applied_observation_ids": list(already or []), "applied_observation_ids": list(applied or []), "state_snapshot": deepcopy(state), "conflicts": deepcopy(conflicts or []), "limitations": ["explicit_apply_only", "process_local_applied_ledger", "no_ui_integration", "no_persistence", "no_provider_calls"]}
