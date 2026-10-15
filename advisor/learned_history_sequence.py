"""Bounded causal protocol sequence, supplementing (not replacing) V4 summaries.

Only the delivered public_history is read. Identity references describe public
entry appearances, not hidden roster identities. A later Illusion replacement
links two appearances explicitly and never rewrites preceding event features.
"""
from collections import deque
import re
import numpy as np

from advisor.learned_encoder import fingerprint, identifier
from advisor.learned_public_categories import BITS, token_bits
from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder

VERSION = "showdown-public-categorical-observation-v4-history-sequence-v1"
ABLATED_VERSION = "showdown-public-categorical-observation-v4-history-sequence-ablated-v1"
VERSIONS = (VERSION, ABLATED_VERSION)
TURNS, CAPACITY, APPEARANCES = 6, 64, 64
EVENTS = ("start", "turn", "switch", "drag", "replace", "move", "cant", "faint",
    "-damage", "-heal", "-sethp", "-fail", "-miss", "-immune", "-crit", "-supereffective",
    "-resisted", "-status", "-curestatus", "-boost", "-unboost", "-setboost", "-clearboost",
    "-clearallboost", "-clearpositiveboost", "-clearnegativeboost", "-invertboost", "-start",
    "-end", "-singleturn", "-singlemove", "-activate", "-ability", "-item", "-enditem",
    "-mega", "-formechange", "detailschange", "-transform", "-weather", "-fieldstart",
    "-fieldend", "-fieldactivate", "-sidestart", "-sideend", "-mustrecharge", "-notarget",
    "-prepare", "-hitcount", "-nothing", "-swapboost", "-copyboost")
DETAILS = tuple(sorted(set(("brn", "par", "slp", "frz", "psn", "tox", "fnt", "atk", "def", "spa", "spd", "spe", "accuracy", "evasion",
    "substitute", "taunt", "encore", "confusion", "trapped", "recharge", "healblock", "throatchop", "flashfire",
    "protect", "flinch", "nopp", "truant", "attract", "disable", "imprison", "yawn", "leechseed", "perishsong",
    "reflect", "lightscreen", "auroraveil", "tailwind", "stealthrock", "spikes", "toxicspikes", "stickyweb",
    "trickroom", "sunnyday", "raindance", "sandstorm", "snowscape", "hail", "none",
    "desolateland", "primordialsea", "deltastream", "electricterrain", "grassyterrain", "mistyterrain", "psychicterrain", "heal"))))
EVENT_IDS = {v:i+2 for i,v in enumerate(EVENTS)}  # 0 padding, 1 unsupported event
DETAIL_IDS = {v:i+3 for i,v in enumerate(DETAILS)}  # 1 unknown, 2 not applicable
FIELDS = (("event",6), ("actor",7), ("recipient",7), ("actor_species",BITS["species"]),
    ("recipient_species",BITS["species"]), ("moves",BITS["moves"]), ("abilities",BITS["abilities"]),
    ("items",BITS["items"]), ("detail",7))
NUMERIC, META = 12, 4
ROW = sum(w for _,w in FIELDS) + NUMERIC
EXTRA = CAPACITY * ROW + META
OLD_DIMENSION = StrategicPublicCategoricalEncoder.dimension
ADMIN = {"", "poke", "clearpoke", "teampreview", "teamsize", "player", "gen", "gametype", "tier", "rule",
    "rated", "upkeep", "t:", "win", "tie", "message", "raw", "html", "c", "c:", "j", "l", "n", "debug", "hint", "-hint", "-message", "-anim"}
PRIVATE = {"split", "request", "sideupdate", "input", "seed"}
ENT = re.compile(r"^(p[12])[a-z]?: (.+)$")


def history_sequence(observation, base):
    role = "p1" if observation["side"] == "self" else "p2"
    history = observation["public_history"]
    if not isinstance(history, list) or any(not isinstance(x,str) for x in history):
        raise ValueError("invalid_public_sequence_history")
    # Supplied histories may be partial. No invented earlier absence or state.
    start = next((i for i in range(len(history)-1,-1,-1) if history[i] == "|start"), None)
    lines = history[start:] if start is not None else history
    names, species, active, frames = {}, {}, {}, deque(maxlen=CAPACITY)
    turn, turn_known, serial = 0, False, 0
    event_counts, unknown_payloads = {}, 0
    per_turn = {}

    def entity(text, new=False):
        nonlocal serial
        m = ENT.fullmatch(text)
        if not m:
            return None
        key = (m[1],m[2])
        if new or key not in names:
            serial += 1; names[key] = (m[1],serial)
        return names[key]

    def category(kind, text):
        # A public unrecognized known identity fails closed, like original V4.
        return base.token(kind, text) if text else 1

    for line in lines:
        p=line.split("|")
        if len(p)<2:
            continue
        event,args=p[1],p[2:]
        if event in PRIVATE:
            raise ValueError("private_protocol_in_public_sequence")
        if event in ADMIN:
            continue
        if event=="turn":
            if not args or not args[0].isdigit() or not 0<int(args[0])<=65535 or (turn_known and int(args[0])<=turn):
                raise ValueError("noncausal_public_sequence_turn")
            turn,turn_known=int(args[0]),True
        actor,recipient=None,None
        actor_role=recipient_role=None
        old_active = active.get(args[0][:2]) if args else None
        if event in {"switch","drag","replace"} and len(args)>=2:
            actor=entity(args[0],True)
            if actor:
                species[actor]=category("species",args[1]);active[actor[0]]=actor
            if event=="replace":recipient=old_active  # explicit public alias revelation
        elif event in {"move","cant","faint","-mustrecharge","-prepare","-transform","-miss"}:
            actor=entity(args[0]) if args else None
            if event=="move" and len(args)>2:recipient=entity(args[2])
            if event in {"-transform","-miss"} and len(args)>1:recipient=entity(args[1])
        elif event not in {"start","turn"}:
            recipient=entity(args[0]) if args and event not in {"-sidestart","-sideend"} else None
            for a in args:
                if a.startswith("[of] "):actor=entity(a[5:])
        if event in {"detailschange","-formechange"} and recipient and len(args)>1:
            species[recipient]=category("species",args[1])
        actor_role=actor[0] if actor else None
        recipient_role=recipient[0] if recipient else (args[0][:2] if args and event in {"-sidestart","-sideend"} and args[0][:2] in ("p1","p2") else None)
        payload={"moves":1,"abilities":1,"items":1,"detail":2}
        detail = (args[1] if len(args)>1 and event in {"cant","-fail","-status","-curestatus","-boost","-unboost","-setboost",
            "-start","-end","-activate","-singleturn","-singlemove","-sidestart","-sideend"} else
            args[0] if args and event in {"-weather","-fieldstart","-fieldend","-fieldactivate"} else None)
        if event in {"move","-prepare"} and len(args)>1:payload["moves"]=category("moves",args[1])
        if event=="-ability" and len(args)>1:payload["abilities"]=category("abilities",args[1])
        if event in {"-item","-enditem"} and len(args)>1:payload["items"]=category("items",args[1])
        if event=="-mega" and len(args)>2:payload["items"]=category("items",args[2])
        for text in ([detail] if detail else []) + args:
            for prefix,kind in (("ability: ","abilities"),("item: ","items"),("move: ","moves")):
                stripped=text.removeprefix("[from] ")
                if stripped.startswith(prefix):payload[kind]=category(kind,stripped[len(prefix):])
        if detail:
            key=identifier(detail.removeprefix("move: ").removeprefix("ability: ").removeprefix("item: "))
            payload["detail"]=DETAIL_IDS.get(key,1)
        unknown=payload["detail"]==1 or event not in EVENT_IDS
        unknown_payloads += unknown
        event_counts[event]=event_counts.get(event,0)+1
        amount=None
        if event in {"-boost","-unboost","-setboost"} and len(args)>2 and re.fullmatch(r"-?\d+",args[2]):
            amount=int(args[2])*(-1 if event=="-unboost" else 1)
            if abs(amount)>10:raise ValueError("unsupported_public_sequence_amount")
        healths=[(recipient,args[1])] if event in {"-damage","-heal","-sethp"} and len(args)>1 else [(None,None)]
        # Pinned Pain Split normally emits one -sethp per target followed by
        # [from]/[silent] tags. Only an actual public entity starts a second pair.
        if event=="-sethp" and len(args)>3 and ENT.fullmatch(args[2]):
            healths.append((entity(args[2]),args[3]))
        for health_recipient,condition in healths:
            affected=health_recipient if condition is not None else recipient
            hp,hp_known=0.,False
            if condition is not None:
                hp_text=condition.split()[0]
                match=re.fullmatch(r"(\d+)/(\d+)[rgy]?",hp_text)
                if hp_text=="0":hp_known=True
                elif match and 0<=int(match[1])<=int(match[2]) and int(match[2])>0:
                    hp=int(match[1])/int(match[2]);hp_known=True
                else:raise ValueError("malformed_public_sequence_health")
            rr=affected[0] if affected else recipient_role
            # References and species are captured NOW, never from later reveals.
            frame={"event":EVENT_IDS.get(event,1),"actor":actor,"recipient":affected,
                "actor_species":species.get(actor,1),"recipient_species":species.get(affected,1),**payload,
                "numeric":[1.,float(turn_known),0.,hp,float(hp_known),(amount or 0)/10,float(amount is not None),
                    float(actor_role==role),float(actor_role is not None and actor_role!=role),
                    float(rr==role),float(rr is not None and rr!=role),float(unknown)],"turn":turn}
            frames.append(frame);per_turn[turn]=per_turn.get(turn,0)+1
    cutoff=max(0,turn-(TURNS-1))
    selected=[r for r in frames if r["turn"]>=cutoff]
    recent_count=sum(n for t,n in per_turn.items() if t>=cutoff)
    references={}
    values=[]
    for frame in selected:
        encoded={**frame}
        for field in ("actor","recipient"):
            key=frame[field]
            if key is not None and key not in references:
                if len(references)>=APPEARANCES:raise ValueError("public_sequence_appearance_capacity")
                references[key]=len(references)+3
            encoded[field]=references.get(key,1)  # unknown != padding != established absence
            if frame["event"] in (EVENT_IDS["start"],EVENT_IDS["turn"]):encoded[field]=2
        numeric=list(frame["numeric"]);numeric[2]=min(turn-frame["turn"],TURNS-1)/(TURNS-1)
        values.append([bit for name,width in FIELDS for bit in token_bits(encoded[name],width)]+numeric)
    rows=np.zeros((CAPACITY,ROW),dtype=np.float32)
    if values:rows[:len(values)]=values
    meta=np.array([1.,float(start is not None),float(recent_count>CAPACITY),float(any(r["numeric"][-1] for r in selected))],dtype=np.float32)
    coverage={"encoded_events":len(values),"recent_events_before_tail_cap":recent_count,"tail_truncated":recent_count>CAPACITY,
        "unknown_payload_events_in_episode":unknown_payloads,"event_counts":event_counts,
        "scope":"last_six_public_turns_tail64_public_appearance_not_hidden_individual_identity"}
    return np.concatenate((rows.flatten(),meta)),coverage


class PublicHistorySequenceEncoder(StrategicPublicCategoricalEncoder):
    dimension=OLD_DIMENSION+EXTRA

    def __init__(self,catalog,version=VERSION):
        if version not in VERSIONS:raise ValueError("unsupported_public_sequence_contract")
        self.version=version
        super().__init__(catalog)
        self.base=StrategicPublicCategoricalEncoder(self.catalog)
        self.feature_contract={**self.feature_contract,"schema_version":"showdown-public-history-sequence-contract-v1",
            "version":version,"dimension":self.dimension,"observation_dimension":self.dimension,
            "parent_feature_fingerprint":self.base.catalog_fingerprint,
            "history_sequence":{"turns":TURNS,"capacity":CAPACITY,"row":ROW,"fields":list(map(list,FIELDS)),"numeric_width":NUMERIC,
                "numeric_fields":["present","turn_known","turn_age_div5","display_health_fraction","health_known","amount_div10","amount_known",
                    "actor_own","actor_foe","recipient_own","recipient_foe","unsupported_payload"],
                "meta":["enabled","episode_start_observed","tail_truncated","unsupported_payload_present"],
                "event_ids":EVENT_IDS,"detail_ids":DETAIL_IDS,"appearance_capacity":APPEARANCES,
                "authority":"delivered_public_history_only_no_request_scenario_checkpoint_or_future",
                "identity":"causal_public_entry_appearances_window_local_refs_replace_explicit_link_no_retroactive_illusion_join",
                "unsupported":"event_unknown_and_payload_unknown_flags_not_effect_inference",
                "health":"display_fraction_only_no_new_exact_own_or_opponent_HP_feature",
                "ablation":version==ABLATED_VERSION,"model":"stateless_shared_embedding_GRU16_zero_hidden_each_forward_no_recurrent_PPO",
                "new_path_initialization_seed":91001,"transfer":"V4_weights_new_context_columns_zero_both_fresh_Adam",
                "padding":"right_zero_rows_zero_reference_tokens","compatibility":"original_V4_history_summaries_and_transport_unchanged"}}
        self.catalog_fingerprint=fingerprint(self.feature_contract)

    def encode(self,observation):
        sequence,_=history_sequence(observation,self.base)
        if self.version==ABLATED_VERSION:sequence=np.zeros_like(sequence)
        return np.concatenate((self.base.encode(observation),sequence))

    def sequence_coverage(self,observation):
        return history_sequence(observation,self.base)[1]
