"""Public native hypothesis prototype: fixed-damage, recharge endgame.

No inference over an arbitrary hidden set. Unknown move availability is only
eliminated by public recharge plus two publicly fainted selected teammates.
Current-display HP possibilities are enumerated by the pinned native engine.
This does NOT certify consistency with the entire causal public prefix. The
bounded prototype therefore never turns a model-only proof into a training
target; the missing reconstruction certificate is a terminal scope boundary.
"""
from copy import deepcopy
import json
from hashlib import sha256
from pathlib import Path
import subprocess

from advisor.learned_action_search_teacher import PUBLIC_VERSION, public_teacher_binding
from advisor.learned_action_signals import require_public_equivalence
from advisor.learned_encoder import identifier, fingerprint
from advisor.learned_strategic_public import project_strategic_public
from advisor.showdown_bridge import ShowdownBridge, SHOWDOWN_COMMIT
from advisor.showdown_observation import project_policy_observation
from advisor.learning_resources import atomic_json

VERSION = "bounded-public-native-terminal-teacher-v1"
# No arbitrary effect interpreter: a restrictive, auditable supported prefix.
PREFIX_MOVES = frozenset(("seismictoss", "hyperbeam", "recover", "softboiled",
    "explosion", "splash", "protect"))
PREFIX_EVENTS = frozenset(("", "t:", "player", "teamsize", "gametype", "gen", "tier", "rated",
    "rule", "clearpoke", "poke", "teampreview", "start", "switch", "turn", "move", "faint",
    "-damage", "-heal", "-enditem", "-ability", "-mustrecharge", "cant", "-fail", "upkeep",
    "-crit", "-supereffective", "-resisted", "-immune", "-notarget", "-miss", "-singleturn", "-activate", "hint", "debug"))


def confirmed_item_absence(view, identity, row):
    # The legacy lossy summary can retain a berry name on its subsequent
    # [from] heal line. Explicit loss/gain events, not a heal attribution,
    # establish current possession. Do not change historical V4 features.
    absence = row.get("known_item", {}) is None
    for line in view["public_history"]:
        p = line.split("|")
        if len(p) > 2 and p[2] == identity:
            if p[1] == "-enditem": absence = True
            elif p[1] in ("-item", "-mega"): absence = False
    return absence


def support_conditions(view, catalog):
    """Public evidence only; return a stable reason instead of imputing values."""
    if view["request_state"] != "move" or sum(view["action_mask"]) < 2:
        return "no_nontrivial_move_decision", None
    projection = project_strategic_public(view, catalog)
    if projection["unsupported"]:
        return "unsupported_public_projection", None
    own, foe = projection["active"]
    if own["effects"].get("recharge") is not False:
        return "own_recharge_or_unknown", None
    if foe["effects"].get("recharge") is not True:
        return "opponent_response_availability_not_publicly_forced", None
    own_side, other = view["state"]["self_side"], view["state"]["opponent_side"]
    own_row = own_side["pokemon"].get(own_side["active_identity"], {})
    foe_row = other["pokemon"].get(other["active_identity"], {})
    if identifier(own_row.get("details", "")) != "heracross" or identifier(foe_row.get("details", "")) != "charizard":
        return "outside_fixed_damage_species_scope", None
    if (own_row.get("known_item", {}) not in (None, "leftovers") or
            not confirmed_item_absence(view, foe_row.get("identity"), foe_row)):
        return "item_not_publicly_supported", None
    if own_row.get("current_ability") != "guts":
        return "own_ability_not_publicly_known_passive", None
    foe_ability = foe_row.get("current_ability", {})
    if not isinstance(foe_ability, dict) and foe_ability not in ("blaze", "solarpower"):
        return "unsupported_public_opponent_ability", None
    for row in (own_row, foe_row):
        if row.get("condition", {}) is not None or any(row.get("stat_stages", {}).values()):
            return "status_or_boost_not_supported", None
    if view["state"]["field"] != {"weather": None, "terrain": None}:
        return "nonempty_or_unknown_public_field", None
    # Unknown trapping is preserved as Unknown. With no living bench and a
    # terminal damaging move it cannot change either candidate or response.
    if any(v is not False for k, v in own["effects"].items() if k != "trapped"):
        return "own_effect_not_confirmed_absent", None
    if any(v is not False for k, v in foe["effects"].items() if k not in ("recharge", "trapped")):
        return "opponent_effect_not_confirmed_absent", None
    if own["types"] != ("Bug", "Fighting") or foe["types"] != ("Fire", "Flying"):
        return "nonstandard_current_typing", None
    if any(identifier(p.get("details", "")).startswith(("zoroark", "zorua")) for p in other.get("preview", [])):
        return "appearance_ambiguity", None
    # M-C brings exactly three. Two distinct publicly fainted identities leave
    # only this living active; no hidden switch response may be omitted.
    for side in (own_side, other):
        rows = list(side["pokemon"].values())
        if len(rows) != 3 or sum(p.get("fainted") is True for p in rows) != 2:
            return "remaining_selected_roster_not_publicly_closed", None
    request = view["own_request"].get("active", [{}])[0]
    actions = []
    for a, legal in enumerate(view["action_mask"]):
        if legal and 6 <= a <= 9:
            slot = a-6
            moves = request.get("moves", [])
            if slot < len(moves) and identifier(moves[slot].get("id")) == "seismictoss":
                if moves[slot].get("pp", 0) > 0 and not moves[slot].get("disabled", True):
                    actions.append(a)
    if not actions:
        return "no_legal_observed_fixed_damage_candidate", None
    if len(view["own_request"].get("side", {}).get("pokemon", [])) != 3:
        return "own_selected_roster_unavailable", None
    for line in view["public_history"]:
        p = line.split("|")
        if len(p) < 2 or p[1] not in PREFIX_EVENTS:
            return "unsupported_public_history_event", None
        if p[1] == "move" and (len(p) < 4 or identifier(p[3]) not in PREFIX_MOVES):
            return "unsupported_public_history_move", None
        if p[1] == "-singleturn" and (len(p) < 4 or identifier(p[3]) != "protect"):
            return "unsupported_single_turn_effect", None
        if p[1] == "-activate" and not any("Skill Swap" in x for x in p):
            return "unsupported_public_activation", None
    return None, {"action": actions[0], "scope": VERSION,
        "response": "public_mustrecharge_no_living_selected_bench",
        "utility": "native_immediate_win_saturates_sparse_terminal_return_upper_bound"}


class PublicNativeTeacher:
    version = VERSION

    def __init__(self, *, checkout, catalog, ledger_path, allow_native_execution=False):
        if type(allow_native_execution) is not bool:
            raise ValueError("explicit_native_teacher_execution_flag_required")
        self.checkout = str(checkout)
        self.catalog = json.loads(Path(catalog).read_text(encoding="utf-8"))
        self.ledger_path = str(ledger_path)
        self.allow_native_execution = allow_native_execution

    def assess(self, view, *, policy_id, learning_step):
        public, binding = public_teacher_binding(view, policy_id=policy_id, learning_step=learning_step)
        base = {"schema_version": PUBLIC_VERSION, "provider_version": VERSION, "binding": binding,
            "evidence_scope": "public_only_admission", "status": "abstain", "target": None}
        reason, conditions = support_conditions(public, self.catalog)
        if reason:
            return {**base, "reason": reason, "native_starts": 0}
        ShowdownBridge(self.checkout)._verify_checkout()
        script = Path(__file__).resolve().parents[1]/"tools/showdown_bridge/public-terminal-teacher.cjs"
        payload = {"view": public, "action": conditions["action"], "ledger": self.ledger_path}
        native_source = fingerprint({p.name:sha256(p.read_bytes()).hexdigest() for p in
            (script, script.with_name("environment.cjs"), script.with_name("legal-battle.cjs"),
             script.with_name("deterministic-proof.cjs"))})
        cache = Path(self.ledger_path).parent/"native_public_proofs"/(fingerprint({
            "public": public, "source": native_source, "engine": SHOWDOWN_COMMIT})+".json")
        if cache.exists():
            saved=json.loads(cache.read_text(encoding="utf-8"))
            evidence=saved["evidence"]
            if (saved.get("source_SHA256")!=native_source or
                    saved["evidence_SHA256"]!=fingerprint(evidence)):
                raise ValueError("public_native_proof_receipt_corrupt")
        else:
            if not self.allow_native_execution:
                return {**base,"reason":"native_proof_not_cached_execution_disabled","native_starts":0}
            result = subprocess.run(["node", str(script), self.checkout], input=json.dumps(payload, allow_nan=False),
                capture_output=True, text=True, encoding="utf-8", timeout=45, check=False)
            evidence = json.loads(result.stdout)
            if result.returncode:
                if (evidence.get("status")=="error" and
                        evidence.get("reason")!="public_native_teacher_failed"):
                    return {**base,"reason":evidence["reason"],"native_evidence":evidence}
                raise ValueError("public_native_teacher_backend_failure_no_label")
            cache.parent.mkdir(parents=True,exist_ok=True)
            atomic_json(cache,{"source_SHA256":native_source,"evidence":evidence,
                "evidence_SHA256":fingerprint(evidence)})
        if evidence.get("status") != "proven":
            return {**base, "reason": evidence.get("reason", "incomplete_native_public_proof"),
                "native_evidence": evidence}
        if (evidence.get("engine_commit") != SHOWDOWN_COMMIT or not evidence.get("hypotheses")
                or not evidence.get("complete_HP_domain") or evidence.get("stochastic_draws") != 0):
            raise ValueError("unproven_public_native_teacher_evidence")
        # Every constructed world must preserve the ENTIRE delivered public
        # decision, not just its neural encoding or species/HP summary.
        for row in evidence["hypotheses"]:
            raw = {**deepcopy(public), **row["before"]}
            candidate = project_policy_observation(raw, row["before"]["public_history"])
            require_public_equivalence(public, candidate)
            if (row["terminal_return"] != 1 or row["truncated"] or not row["terminated"]
                    or row["own_choice"]!=public["choices"][conditions["action"]]
                    or row["opponent_choice"]!="move 1" or row["proof"]["stochastic_draws"]!=0
                    or any(s!="spe" for s in row["hidden_stat_reads"])):
                raise ValueError("nonuniform_public_native_win_proof")
        # Matching a copied public log is insufficient. Historical fixed-damage
        # and recovery events constrain possible max HP / spreads jointly. The
        # current-state initializer has no native causal-prefix witness for
        # every world. Do not silently treat a superset/model proof as the
        # required public-consistent hypothesis certificate.
        return {**base, "reason": "causal_public_history_witness_unavailable", "conditions": conditions,
            "native_evidence_scope": "current_state_overapproximation_NOT_teacher_label",
            "native_evidence": evidence, "native_evidence_SHA256": fingerprint(evidence)}
