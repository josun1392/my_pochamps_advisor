"""Integrated public V5 transport. Prediction targets are a separate channel.

Reuses V4, authenticated own HP and causal history; no privileged calculation,
exact damage engine or additional observation of the opponent's true set.
"""
from functools import lru_cache
import numpy as np
from advisor.learned_encoder import fingerprint, identifier
from advisor.learned_strategic_public import StrategicPublicCategoricalEncoder
from advisor.learned_own_hp import own_hp_features, EXTRA as HP_EXTRA
from advisor.learned_history_sequence import history_sequence, EXTRA as HISTORY_EXTRA
from advisor.learned_full_domain import load_inventory
from advisor.learned_public_categories import BITS, token_bits
from advisor.learned_own_identity import own_player_records

VERSION = "showdown-public-categorical-observation-v5-integrated-v1"
APPEARANCE_SUPPORT_VERSION = "showdown-public-categorical-observation-v5-integrated-v2"
VERSIONS = (VERSION, APPEARANCE_SUPPORT_VERSION)
OLD_DIM = StrategicPublicCategoricalEncoder.dimension
TACTICAL = 10
SIZES = {k: 2 ** BITS[k] for k in ("abilities", "items", "moves")}
SUPPORT = sum(SIZES.values())
KNOWN_BITS = BITS["abilities"] + BITS["items"]
PRED_EXTRA = SUPPORT + KNOWN_BITS + SIZES["moves"]
DIMENSION = OLD_DIM + HP_EXTRA + HISTORY_EXTRA + 35 * TACTICAL + PRED_EXTRA
FAMILIES = ("attack", "recovery", "defense", "setup", "status_or_field", "switch")


@lru_cache(maxsize=1)
def inventory():
    return load_inventory()  # Maintained pinned native domain, not a new Dex.


def active_public(view):
    side = view["state"]["opponent_side"]
    identity = side["active_identity"]
    return side["pokemon"].get(identity, {}) if isinstance(identity, str) else {}


def current_public_prediction_knowledge(view):
    row=active_public(view)
    values={"abilities":row.get("current_ability",{"knowledge":"unknown"}),
            "items":row.get("known_item",{"knowledge":"unknown"})}
    last_form=-1;last_ability=-1
    identity=row.get("identity")
    for i,line in enumerate(view["public_history"]):
        p=line.split("|")
        if len(p)>3 and p[2]==identity:
            if p[1] in {"detailschange","-formechange","-transform"}:last_form=i
            if p[1]=="-ability" or (any(a.startswith("[from] ability: ") for a in p[3:]) and not any(a.startswith("[of]") for a in p[3:])):last_ability=i
    if last_form>last_ability:values["abilities"]={"knowledge":"unknown"}
    return values


def prediction_transport(view, encoder, *, version=VERSION):
    """Species/form learnability is public; ability changes widen support safely.

    Moves are marginal presence predictions, not a jointly legal guessed team.
    Item support is the native format-wide held-item domain plus known absence.
    Apparent Illusion identities cannot narrow support to the displayed species.
    A private target outside public support is skipped, never used to widen it.
    """
    inv, row = inventory(), active_public(view)
    name = identifier(row.get("details", ""))
    entries = [inv["species"][name]] if name in inv["species"] else []
    current_entry = entries[0] if entries else None
    ambiguous = row.get("identity_scope") == "public_apparent_identity_unconfirmed"
    if ambiguous:
        entries = [inv["species"][identifier(p["details"])]
                   for p in view["state"]["opponent_side"]["preview"]
                   if identifier(p["details"]) in inv["species"]]
    role = "p2" if view["side"] == "self" else "p1"
    changed = any(("|-transform|" in line or "|-ability|" in line) and role in line
                  for line in view["public_history"])
    moves_changed=any(role in line and ("|-transform|" in line or
        "|-start|" in line and any(m in line.lower() for m in ("mimic","sketch"))) for line in view["public_history"])
    changed |= moves_changed
    supports = {k: np.zeros(n, np.float32) for k,n in SIZES.items()}
    # Current runtime changes may create non-selectable canonical abilities.
    # Inventory `abilities` validates starting sets, including the base set
    # required to reach a Mega. It is NOT the current transformed ability list.
    ability_names = (encoder.tokens["abilities"].keys() if changed or not entries
                     else {a for e in entries for a in (
                         inv["public_dex"][identifier(e["name"])]["abilities"].values()
                         if e["kind"] not in {"selectable","cosmetic"} else e["abilities"])})
    if version == APPEARANCE_SUPPORT_VERSION and current_entry and ambiguous:
        # Illusion uncertainty preserves preview possibilities AND the publicly
        # displayed transformed form's runtime ability domain. Starting-set
        # preview abilities alone omit e.g. publicly displayed Mega Kangaskhan's
        # Parental Bond. Never narrow this union using the private target.
        ability_names = set(ability_names) | set(inv["public_dex"][name]["abilities"].values())
    move_names = (encoder.tokens["moves"].keys() if changed or not entries
                  else {m for e in entries for m in e["moves"]})
    item_names = list(inv["items"])
    for kind, names in (("abilities", ability_names), ("items", item_names), ("moves", move_names)):
        for value in names:
            key = identifier(value)
            if key in encoder.tokens[kind]: supports[kind][encoder.tokens[kind][key]] = 1
    supports["items"][2] = 1  # confirmed no item is distinct from Unknown.
    known = []
    knowledge=current_public_prediction_knowledge(view)
    for kind, field in (("abilities", "current_ability"), ("items", "known_item")):
        value = knowledge[kind]
        # The unchanged V4 summary can retain a pre-Mega revealed ability.
        # A newer public formechange invalidates its CURRENT-value binding.
        # Do not erase that historical identity or consult private truth.
        token = 1 if isinstance(value, dict) else 2 if value is None else encoder.token(kind,value)
        # Known public runtime identity is evidence, not a private-set inference.
        if token > 1: supports[kind][token] = 1
        known += token_bits(token, BITS[kind])
    moves = np.zeros(SIZES["moves"],np.float32)
    for m in row.get("known_moves", []):
        token=encoder.token("moves",m); supports["moves"][token]=1
        if not moves_changed:moves[token]=1
    if any(not v.any() for v in supports.values()):
        raise ValueError("empty_public_v5_prediction_support")
    return np.concatenate([supports[k] for k in SIZES]+[np.asarray(known,np.float32),moves])


def tactical_features(view, base):
    """Nominal offense, NOT exact damage/KO/speed; unsupported values flagged.

    New nominal index uses own authenticated attack stat and confirmed public
    current typing. Missing opposing stats/modifiers are never fabricated.
    """
    result=np.zeros((35,TACTICAL),np.float32)
    projection=base.project(view); foe_types=projection["active"][1]["types"]
    own=view["state"]["self_side"]
    opponent=active_public(view)
    roster=view["own_request"].get("side",{}).get("pokemon",[])
    active=next((p for p in roster if p.get("active")),None)
    slots=view["own_request"].get("active",[{}])[0].get("moves",[])
    # Native pinned type chart via existing catalogue's pure-type witnesses.
    if not hasattr(base,"_v5_type_witnesses"):
        base._v5_type_witnesses={}
        for name,p in base.catalog["species"].items():
            if len(p["types"])==1:base._v5_type_witnesses.setdefault(p["types"][0],name)
    witnesses=base._v5_type_witnesses
    foe=base.catalog["species"].get(identifier(opponent.get("details","")),{})
    for a,legal in enumerate(view["action_mask"]):
        if not legal or a==26: continue
        switch=a<6
        p=roster[a] if switch and a<len(roster) else active
        if not p:continue
        stats=p.get("stats",{})
        own_species=base.catalog["species"].get(identifier(p.get("details","")),{})
        if switch: mids=p.get("moves",[])
        else:
            offset=31 if a>=31 else 27 if a>=27 else 22 if a>=22 else 18 if a>=18 else 14 if a>=14 else 10 if a>=10 else 6
            mids=[slots[a-offset]["id"]] if a-offset<len(slots) else []
        strengths=[]
        for mid in mids:
            m=base.catalog["moves"].get(identifier(mid),{})
            if m.get("category") not in ("Physical","Special") or not m.get("power"):continue
            attack=stats.get("atk" if m["category"]=="Physical" else "spa")
            if attack is None or not foe_types:continue
            eff=1.
            for t in foe_types:
                witness=witnesses.get(t)
                if witness is None:eff=None;break
                eff*=base.catalog["effectiveness"].get(m["type"],{}).get(witness,1.)
            if eff is not None:
                own_types=own_species.get("types",[]) if switch else projection["active"][0]["types"]
                if own_types is not None:
                    strengths.append(min(4.,m["power"]/150*attack/512*eff*(1.5 if m["type"] in own_types else 1.)))
        known_moves=opponent.get("known_moves",[])
        defensive=[base.catalog["effectiveness"].get(base.catalog["moves"].get(m,{}).get("type"),{}).get(identifier(p["details"]),1.)
                   for m in known_moves if base.catalog["moves"].get(m,{}).get("category") in ("Physical","Special")]
        result[a]=[max(strengths,default=0),float(bool(strengths)),stats.get("spe",0)/512,float("spe" in stats),
                   foe.get("base_stats",{}).get("spe",0)/255,float(bool(foe)),max(defensive,default=0)/4,
                   float(bool(defensive)),0,1]
    return result


class IntegratedCombatV5Encoder(StrategicPublicCategoricalEncoder):
    dimension=DIMENSION
    def __init__(self,catalog,*,version=VERSION):
        if version not in VERSIONS:raise ValueError("unsupported_integrated_v5_contract")
        super().__init__(catalog);self.version=version
        self.base=StrategicPublicCategoricalEncoder(self.catalog)
        self.tactics=self.base.legacy.base.tactics
        self.feature_contract={**self.base.feature_contract,"schema_version":"showdown-integrated-combat-v5-contract-v1",
            "version":version,"dimension":DIMENSION,"observation_dimension":DIMENSION,
            "parent_feature_fingerprint":self.base.catalog_fingerprint,
            "layout":"unchanged_V4_then_ownHP24_history5636_tactical350_prediction_public_support",
            "hp_owner":"own_hp_features_native_authenticated_identity",
            "history_owner":"history_sequence_6turns_tail64_stateless_GRU16",
            "tactical_fields":["nominal_offense_not_damage","nominal_known","own_request_speed_div512","own_speed_known",
                "foe_base_speed_prior_div255","prior_known","revealed_move_defensive_type_prior_div4","defensive_prior_known",
                "exact_damage_available","hidden_modifier_uncertainty"],
            "prediction":"next_public_executed_family_and_current_active_marginal_moves_ability_item_not_joint_legal_set",
            "sizes":SIZES,"families":list(FAMILIES),"public_support":"pinned_native_species_learnsets_Illusion_union_runtime_widening",
            "current_form_ability_support":"native_public_dex_current_transformed_form_not_starting_set_ability_domain_v1",
            "current_ability_binding":"invalidate_pre_formechange_reveal_until_newer_public_ability_evidence_legacy_V4_prefix_preserved",
            "private_supervision":"separate_coordinator_targets_never_actor_or_critic_forward_input",
            "transfer":"V4_compatible_tensors_new_columns_zero_fresh_Adam",
            "search":"disabled_no_hidden_truth_search"}
        if version == APPEARANCE_SUPPORT_VERSION:
            self.feature_contract["appearance_support"] = "Illusion_preview_union_plus_public_current_form_native_ability_domain_v2"
        self.catalog_fingerprint=fingerprint(self.feature_contract)
    def encode(self,view):
        if any(k in view for k in ("native_state","teams","scenario","checkpoint","seed","future_seed",
                                   "input_log","opponent_request","coordinator_v5_supervision","auxiliary_labels")):
            raise ValueError("privileged_input_in_v5_public_observation")
        old=self.base.encode(view);history,_=history_sequence(view,self.base)
        return np.concatenate((old,own_hp_features(view).flatten(),history,
                               tactical_features(view,self.base).flatten(),prediction_transport(view,self.base,version=self.version)))
