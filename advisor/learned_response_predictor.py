"""Offline Foundation-selected response prediction; never a combat policy.

One observer's authenticated public view is the only forward input. Opposite
requests/masks authenticate labels in a separate coordinator function. The
output is revealed move identity, unrevealed move family, or voluntary switch;
it is NOT a probability over the opponent's privately legal 35 action slots.
"""
from copy import deepcopy
from collections import Counter
import re
import numpy as np

from advisor.learned_encoder import PartialObservationEncoder, fingerprint, identifier
from advisor.learned_combat_v5 import FAMILIES, active_public

VERSION = "foundation-public-selected-response-predictor-v1"
FEATURE_KEYS = ("schema_version", "interpretation", "side", "turn", "request_state",
                "own_request", "visible_active_health", "action_schema_version",
                "action_mask", "choices", "state", "public_history")
FORBIDDEN = frozenset(("native_state", "seed", "checkpoint", "scenario", "teams",
    "queue", "opponent_request", "target_request", "target_mask", "probabilities",
    "value", "result", "future", "labels", "coordinator_v5_supervision"))
DEFENSE = frozenset(("protect", "detect", "endure", "substitute", "wideguard",
    "kingsshield", "spikyshield", "banefulbunker", "obstruct", "silktrap", "burningbulwark"))


def public_input(view):
    if FORBIDDEN & set(view):
        raise ValueError("private_predictor_input")
    side = {"self": "p1", "opponent": "p2"}.get(view.get("side"))
    request = view.get("own_request", {}).get("side", {})
    if side is None or request and request.get("id") != side:
        raise ValueError("predictor_observer_request_identity")
    mask = view.get("action_mask", [])
    if len(mask) != 35 or any(v not in (0, 1, False, True) for v in mask) or not any(mask):
        raise ValueError("predictor_public_mask")
    return {key: deepcopy(view[key]) for key in FEATURE_KEYS if key in view}


def move_family(mid, tactics, native):
    t, n = tactics.get(mid, {}), native.get(mid, {})
    if mid in ("rest", "wish") or t.get("heal") and t.get("target") in ("self", "allies"):
        return "recovery"
    if mid in DEFENSE:
        return "defense"
    if t.get("target") == "self" and any(v > 0 for v in t.get("boosts", {}).values()):
        return "setup"
    if n.get("category") in ("Physical", "Special"):
        return "attack"
    return "status_or_field"


def selected_label(observer, target, action, result, tactics, native):
    """Private target data are read only here, never forwarded to the encoder."""
    if observer["side"] == target["side"] or observer["episode_id"] != target["episode_id"] or observer["revision"] != target["revision"]:
        raise ValueError("predictor_label_role_or_time")
    public_input(observer)
    public_input(target)  # validate ownership, not an input transformation
    if type(action) is not int or not 0 <= action < 35 or not target["action_mask"][action]:
        raise ValueError("predictor_illegal_recorded_label")
    if result["action_rejected"]:
        return None, "native_rejected_attempt"
    if action == 26 or target["action_mask"][26]:
        return None, "target_wait"
    if target["request_state"] != "move":
        return None, "forced_or_administrative_replacement"
    if observer["request_state"] != "move" or observer["action_mask"][26]:
        return None, "observer_not_joint_move_decision"
    if action < 6:
        return {"semantic": "switch", "family": "switch", "mid": None}, None
    match = re.search(r"\bmove (\d+)", str(target["choices"][action]))
    moves = target["own_request"].get("active", [{}])[0].get("moves", [])
    if not match or not 0 <= int(match[1])-1 < len(moves):
        raise ValueError("predictor_selected_move_slot_unavailable")
    mid = identifier(moves[int(match[1])-1]["id"])
    if mid not in native:
        raise ValueError("predictor_unknown_selected_move:" + mid)
    family = move_family(mid, tactics, native)
    known = {identifier(m) for m in active_public(observer).get("known_moves", [])}
    return {"semantic": "known:"+mid if mid in known else "unknown:"+family,
            "family": family, "mid": mid}, None


class ResponseEncoder:
    """787 existing numerical features + exact public active species and moves.

    The output support is public revelations plus five unknown-move families
    and switch. No private legality, hidden learnset or selected-three lookup.
    """
    def __init__(self, catalog, tactics, native):
        self.base = PartialObservationEncoder(catalog)
        self.catalog, self.tactics, self.native = self.base.catalog, tactics, native
        self.species = tuple(sorted(self.catalog["species"]))
        self.moves = tuple(sorted(native))
        self.outputs = tuple("known:"+m for m in self.moves) + tuple("unknown:"+f for f in FAMILIES if f != "switch") + ("switch",)
        self.output_index = {name:i for i,name in enumerate(self.outputs)}
        self.move_index = {m:i for i,m in enumerate(self.moves)}
        self.species_index = {m:i for i,m in enumerate(self.species)}
        self.family_index = np.asarray([FAMILIES.index(move_family(m, tactics, native)) for m in self.moves]
            + [FAMILIES.index(f) for f in FAMILIES if f != "switch"] + [FAMILIES.index("switch")])
        self.dimension = 787 + 2*(len(self.species)+1) + len(self.moves)
        self.identity = {"schema_version":VERSION, "dimension":self.dimension, "outputs":self.outputs,
            "base":self.base.version, "catalog":fingerprint(self.catalog),
            "native":fingerprint(native), "tactics":fingerprint(tactics),
            "support":"public_revealed_current_actor_moves_plus_unknown_families_and_switch",
            "no_private_target_mask_in_forward_or_normalization":True}
        self.fingerprint = fingerprint(self.identity)

    def encode(self, view):
        view = public_input(view)
        base = self.base.encode(view)
        if base.shape != (787,):
            raise ValueError("predictor_legacy_feature_shape")
        species = np.zeros(2*(len(self.species)+1), np.float32)
        for i, key in enumerate(("self_side", "opponent_side")):
            side = view["state"][key]
            active = side["pokemon"].get(side["active_identity"], {})
            sid = identifier(active.get("details", ""))
            species[i*(len(self.species)+1)+self.species_index.get(sid,len(self.species))] = 1
        moves = np.zeros(len(self.moves), np.float32)
        for mid in active_public(view).get("known_moves", []):
            mid = identifier(mid)
            if mid not in self.move_index:
                raise ValueError("predictor_unsupported_public_move:"+mid)
            moves[self.move_index[mid]] = 1
        support = np.concatenate((moves.astype(bool), np.ones(6, bool)))
        x = np.concatenate((base,species,moves)).astype(np.float32)
        if x.shape != (self.dimension,) or not np.isfinite(x).all():
            raise ValueError("invalid_predictor_features")
        return x, support

    def heuristic(self, view):
        """Fixed public nominal-power/matchup + health-gap response baseline.

        Uses maintained type-only priors, not exact damage, private target
        moves or BR's uncalibrated scenario weights. Positive uncertainty floor.
        """
        _, support = self.encode(view)
        foe = active_public(view)
        own = view["state"]["self_side"]
        active = own["pokemon"].get(own["active_identity"], {})
        own_sid = identifier(active.get("details", ""))
        foe_sid = identifier(foe.get("details", ""))
        types = self.catalog["species"].get(foe_sid, {}).get("types", [])
        hp = foe.get("hp_fraction")
        gap = 1-hp if isinstance(hp,(float,int)) else .5
        weights = np.zeros(len(self.outputs), np.float64)
        for i in np.flatnonzero(support[:len(self.moves)]):
            mid=self.moves[i]; m=self.native[mid]; family=move_family(mid,self.tactics,self.native)
            if family=="attack":
                eff=self.catalog["effectiveness"].get(m.get("type"),{}).get(own_sid,1.)
                weights[i]=.1+max(0,float(m.get("power",0)))*eff*(1.5 if m.get("type")in types else 1)/40
            else:
                weights[i]={"recovery":.1+3*gap,"defense":.3,"setup":.3,"status_or_field":.4}[family]
        for name,weight in (("attack",2.),("recovery",.1+gap),("defense",.15),("setup",.15),("status_or_field",.3)):
            weights[self.output_index["unknown:"+name]]=weight
        weights[-1]=.4
        return normalize_public(weights,support)


def normalize_public(weights, support):
    weights=np.asarray(weights,dtype=np.float64); support=np.asarray(support,dtype=bool)
    if weights.shape!=support.shape or not support.any() or not np.isfinite(weights).all() or (weights<0).any():
        raise ValueError("invalid_public_response_distribution")
    p=np.where(support,weights,0.)
    if p.sum()<=0:
        raise ValueError("empty_public_response_distribution")
    return p/p.sum()


def frequency_predictions(train_labels, supports, output_count):
    counts=np.bincount(train_labels,minlength=output_count).astype(float)+.5
    p=np.asarray(supports,dtype=float)*counts
    return p/p.sum(axis=1,keepdims=True)


def score_predictions(probabilities, labels, family_index):
    p=np.asarray(probabilities,dtype=np.float64); y=np.asarray(labels,dtype=int)
    if len(y)==0 or p.shape[0]!=len(y) or not np.isfinite(p).all() or not np.allclose(p.sum(1),1,atol=1e-6):
        raise ValueError("invalid_prediction_score")
    nll=-np.log(np.maximum(p[np.arange(len(y)),y],1e-12))
    brier=(p*p).sum(1)-2*p[np.arange(len(y)),y]+1
    correct=(p.argmax(1)==y)
    confidence=p.max(1); bins=[]
    for low in np.arange(0,1,.1):
        ix=(confidence>=low)&(confidence<low+.1 if low<.9 else confidence<=1)
        if ix.any(): bins.append({"low":float(low),"n":int(ix.sum()),"confidence":float(confidence[ix].mean()),"accuracy":float(correct[ix].mean())})
    fp=np.zeros((len(y),len(FAMILIES)))
    for i,f in enumerate(family_index): fp[:,f]+=p[:,i]
    fy=family_index[y]
    by_family={f:{"n":int((fy==i).sum()),"nll":float(nll[fy==i].mean()),
        "family_recall":float((fp.argmax(1)[fy==i]==i).mean())} for i,f in enumerate(FAMILIES) if (fy==i).any()}
    return {"rows":len(y),"nll":float(nll.mean()),"brier":float(brier.mean()),"top1":float(correct.mean()),
        "family_top1":float((fp.argmax(1)==fy).mean()),"family_brier":float(((fp*fp).sum(1)-2*fp[np.arange(len(y)),fy]+1).mean()),
        "ece10":float(sum(b["n"]*abs(b["confidence"]-b["accuracy"]) for b in bins)/len(y)),
        "calibration_bins":bins,"families":by_family}, {"nll":nll,"brier":brier,"top1":correct.astype(float)}


def make_model(input_dim, output_dim):
    import torch
    return torch.nn.Sequential(torch.nn.Linear(input_dim,128),torch.nn.Tanh(),
        torch.nn.Linear(128,64),torch.nn.Tanh(),torch.nn.Linear(64,output_dim))


def model_probabilities(model, x, support, temperature=1.):
    import torch
    logits=model(x)/temperature
    return torch.softmax(logits.masked_fill(~support,-1e9),dim=-1)


def team_signature(team):
    """Ignore display names, roster and move ordering, preserve full set facts."""
    rows=[]
    for mon in team:
        row={k:deepcopy(v) for k,v in mon.items() if k not in ("name","nickname")}
        if "moves" in row: row["moves"]=sorted(row["moves"])
        rows.append(row)
    return fingerprint(sorted(rows,key=fingerprint))


def audit_split(cases):
    ownership={}; seeds=set(); signatures=set(); counts=Counter()
    for c in cases:
        fold=c["fold"]; counts[fold]+=1
        key=tuple(c["scenario"]["seed"])
        if key in seeds: raise ValueError("duplicate_predictor_native_seed")
        seeds.add(key)
        for team in c["scenario"]["teams"].values():
            h=team_signature(team)
            if h in ownership and ownership[h]!=fold:
                raise ValueError("predictor_full_team_split_leak")
            ownership[h]=fold
        h=fingerprint(c["scenario"])
        if h in signatures: raise ValueError("duplicate_predictor_scenario")
        signatures.add(h)
    if set(counts)!={"train","validation","test"} or min(counts.values())<24:
        raise ValueError("insufficient_predictor_case_split")
    return dict(counts)
