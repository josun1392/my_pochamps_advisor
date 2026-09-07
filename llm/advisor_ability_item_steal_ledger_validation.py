"""Narrow terminal item-steal evidence validation for existing pair ledgers."""
from copy import deepcopy
from typing import Mapping

from llm.advisor_runtime_d0_ability_item_steal_completion_authority import resolve_ability_item_steal_removability
from llm.advisor_runtime_d0_canonical_contact_classification_authority import canonical_move_contact_metadata
from llm.advisor_runtime_d0_life_orb_immediate_authority import _sheer_force_applicability


def validate_ability_item_steal_leaf(leaf, *, envelope=None, native_terminal=None, pair_base=None, first_action=False):
    if not isinstance(leaf, Mapping):
        return "ability_steal_leaf_invalid"
    p, c = leaf.get("provenance", {}), leaf.get("consequences", {})
    effect = c.get("ability_item_steal")
    authority = p.get("ability_item_steal_completion_authority")
    envelope = envelope if envelope is not None else p.get("ability_item_steal_terminal_effect")
    if effect is None and authority is None and envelope is None:
        return None
    if not isinstance(effect, Mapping) or effect != authority or not isinstance(envelope, Mapping) or effect != envelope.get("effect_authority"):
        return "ability_steal_evidence_missing_or_mismatched"
    if effect.get("schema_version") != "runtime-d0-ability-item-steal-completion-authority-v1" or effect.get("status") != "resolved" or envelope.get("schema_version") != "detached-completed-action-terminal-effect-adapter-v1" or envelope.get("status") != "resolved":
        return "ability_steal_schema_invalid"
    if isinstance(pair_base, Mapping):
        if effect.get("session_id") != pair_base.get("session_id") or p.get("attacker") not in (pair_base.get("own_actor"), pair_base.get("opponent_actor")):
            return "ability_steal_foreign_pair"
        if first_action and effect.get("source_runtime_fingerprint") != pair_base.get("source_runtime_fingerprint"):
            return "ability_steal_stale_pair_runtime"
        if first_action and p.get("attacker") == pair_base.get("own_actor") and effect.get("source_branch_fingerprint") != pair_base.get("source_branch_fingerprint"):
            return "ability_steal_foreign_pair_branch"
    source, witness = envelope.get("terminal_source"), envelope.get("source_leaf")
    if not isinstance(source, Mapping) or not isinstance(witness, Mapping) or source.get("terminal") is not True:
        return "ability_steal_nonterminal_source"
    if native_terminal is not None and source.get("native_terminal") != native_terminal:
        return "ability_steal_foreign_native_terminal"
    if source.get("native_terminal", {}).get("terminal") is not True or source.get("terminal_id") != source.get("native_terminal", {}).get("edge_id"):
        return "ability_steal_terminal_identity_invalid"
    family = source.get("family")
    expected_family = {"population-bomb": "population_bomb", "triple-axel": "triple_axel", "triple-kick": "triple_kick", "bullet-seed": "variable_two_to_five_hit", "rock-blast": "variable_two_to_five_hit"}.get(p.get("move_id"), "fixed_two_hit" if "ordered_hits" in leaf else "ordinary_single_hit")
    if family != expected_family or source.get("actor") != p.get("attacker") or source.get("target") != p.get("target"):
        return "ability_steal_source_owner_invalid"
    if any(source.get(k) != effect.get(k) for k in ("action_id", "move_id")) or effect.get("action_id") != leaf.get("candidate_id") or effect.get("move_id") != p.get("move_id"):
        return "ability_steal_action_invalid"
    if any(effect.get(k) != p.get(k) for k in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) or effect.get("source_leaf_id") != leaf.get("leaf_id") or effect.get("source_branch_path") != leaf.get("branch_path"):
        return "ability_steal_stale_or_foreign_path"
    original = deepcopy(dict(leaf))
    original["consequences"].pop("ability_item_steal", None)
    original["provenance"].pop("ability_item_steal_completion_authority", None)
    original["provenance"].pop("ability_item_steal_terminal_effect", None)
    if original != witness:
        return "ability_steal_source_leaf_changed"
    direction = effect.get("trigger_direction")
    if direction not in {"magician_attacker_hit", "pickpocket_defender_contact"}:
        return "ability_steal_direction_invalid"
    receiver, donor = (p.get("attacker"), p.get("target")) if direction == "magician_attacker_hit" else (p.get("target"), p.get("attacker"))
    if effect.get("receiver") != receiver or effect.get("ability_holder") != receiver or effect.get("donor") != donor or effect.get("ability_id") != direction.split("_")[0]:
        return "ability_steal_holder_or_direction_invalid"
    ability = effect.get("ability_state", {})
    if ability.get("status") != "active" or ability.get("value") != effect.get("ability_id") or ability.get("neutralizing_gas_active") is not False:
        return "ability_steal_ability_not_active"
    completion = effect.get("completion", {})
    if completion.get("status") != "completed" or any(completion.get(k) != source.get(k) for k in ("terminal_id", "terminal_reason", "action_id", "move_id")):
        return "ability_steal_completion_invalid"
    if family in {"ordinary_single_hit", "fixed_two_hit"} and source.get("terminal_id") != leaf.get("leaf_id"):
        return "ability_steal_foreign_terminal"
    if leaf.get("hit_state") != "hit" or c.get("source_hit_context", {}).get("target_routing", "target") != "target" or c.get("own_final_hp") == 0 or (direction.startswith("pickpocket") and c.get("target_final_hp") == 0):
        return "ability_steal_inapplicable_attack"
    if family in {"ordinary_single_hit", "fixed_two_hit"} and not ((isinstance(c.get("damage"), int) and c["damage"] > 0) or any(isinstance(hit, Mapping) and hit.get("actual_damage", 0) > 0 and hit.get("target_routing") == "target" for hit in leaf.get("ordered_hits", ()))):
        return "ability_steal_unsuccessful_attack"
    contact = effect.get("contact")
    sheer = effect.get("sheer_force_trigger_applicability")
    if direction.startswith("pickpocket"):
        canonical = canonical_move_contact_metadata(p.get("move_id"))
        if canonical.get("contact_state") != "contact" or c.get("contact") != "successful_contact_eligible" or not isinstance(contact, Mapping) or contact.get("is_contact") is not True or contact.get("source_leaf_id") != leaf.get("leaf_id"):
            return "ability_steal_forged_contact"
        if not isinstance(sheer, Mapping) or sheer != envelope.get("sheer_force") or sheer.get("status") != "resolved" or sheer.get("canonical_applicability") != _sheer_force_applicability({"move_id": p["move_id"]}):
            return "ability_steal_forged_sheer_force"
        blocked = sheer.get("attacker_ability") == "sheer-force" and sheer.get("defender_ability") != "neutralizing-gas" and sheer["canonical_applicability"].get("boosted") is True
        if sheer.get("prevents_trigger") is not False or blocked or any(sheer.get(k) != effect.get(k) or contact.get(k) != effect.get(k) for k in ("action_id", "move_id")):
            return "ability_steal_forged_sheer_force"
    legality = effect.get("transfer_legality", {})
    removable = resolve_ability_item_steal_removability(item_authority=effect.get("donor_item_before"), target_species=effect.get("donor_species"))
    if legality.get("status") != "resolved" or legality.get("donor") != donor or legality.get("removability_authority") != removable or removable.get("removable") is not True or legality.get("transferable") is not True or legality.get("sticky_hold_active") is not False or legality.get("donor_ability") in {"sticky-hold", "neutralizing-gas"} or legality.get("neutralizing_gas_active") is not False:
        return "ability_steal_forged_transfer_legality"
    if direction.startswith("pickpocket") and (sheer.get("attacker_ability") != legality.get("donor_ability") or sheer.get("defender_ability") != ability.get("value")):
        return "ability_steal_conflicting_ability_evidence"
    item = effect.get("item")
    if not isinstance(item, str) or effect.get("outcome") != "transferred" or effect.get("receiver_item_before", {}).get("status") != "known_absent" or effect.get("receiver_item_before", {}).get("value") is not None or effect.get("donor_item_before", {}).get("status") != "known" or effect.get("donor_item_before", {}).get("value") != item or effect.get("receiver_item_after") != {"status": "known", "value": item} or effect.get("donor_item_after") != {"status": "known_absent", "value": None}:
        return "ability_steal_nonatomic_ownership"
    before, after = envelope.get("detached_state_before"), envelope.get("detached_state_after")
    if not isinstance(before, Mapping) or not isinstance(after, Mapping) or envelope.get("result") != "applied":
        return "ability_steal_detached_state_invalid"
    if any(before.get(k) != effect.get(k) for k in ("session_id", "source_runtime_fingerprint", "source_branch_fingerprint")) or before.get("first_action", {}).get("leaf_id") != leaf.get("leaf_id"):
        return "ability_steal_detached_state_foreign"
    expected = deepcopy(dict(before))
    for owner, name in ((receiver, "receiver"), (donor, "donor")):
        active = expected.get("active", {}).get(owner.get("side"), {})
        if active.get("owner") != owner or any(active.get("hypothetical_item", {}).get(k) != effect[f"{name}_item_before"].get(k) for k in ("status", "value")):
            return "ability_steal_branch_item_mismatch"
        active["hypothetical_item"] = deepcopy(effect[f"{name}_item_after"])
    return None if expected == after else "ability_steal_detached_projection_invalid"
