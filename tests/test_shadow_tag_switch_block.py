from llm.advisor_shadow_tag_switch_block import aggregate_hard_blockers, derive_magnet_pull_block, derive_shadow_tag_block, resolve_effective_switch_permission

AUTH={"session_id":"s","source":{"pokemon_id":"x"},"target":{"pokemon_id":"a"},"ability_id":"shadow-tag","applicability":"applicable","interaction":"affecting"}
TYPE={"status":"known","types":["normal"]}; ITEM={"status":"known_absent","value":None}; ABILITY={"status":"known","value":"pressure"}
def test_block_and_exceptions_are_block_only():
    assert derive_shadow_tag_block(authority=AUTH,self_type=TYPE,self_item=ITEM,self_ability=ABILITY)["state"]=="confirmed_blocked"
    assert derive_shadow_tag_block(authority=AUTH,self_type={"status":"known","types":["ghost"]},self_item=ITEM,self_ability=ABILITY)["state"]=="exception_applies"
    assert derive_shadow_tag_block(authority=AUTH,self_type=TYPE,self_item={"status":"unknown"},self_ability=ABILITY)["state"]=="insufficient_context"
def test_manual_permission_is_only_vetoed_by_confirmed_block():
    assert resolve_effective_switch_permission({"status":"permitted"},{"state":"insufficient_context"})=={"status":"permitted"}
    assert resolve_effective_switch_permission({"status":"permitted"},{"state":"confirmed_blocked"})=={"status":"blocked"}

def test_magnet_pull_requires_steel_and_respects_ghost_shed_shell_and_aggregation():
    authority={**AUTH,"ability_id":"magnet-pull"}; steel={"status":"known","types":["steel"]}
    magnet=derive_magnet_pull_block(authority=authority,self_type=steel,self_item=ITEM)
    assert magnet["state"]=="confirmed_blocked"
    assert derive_magnet_pull_block(authority=authority,self_type={"status":"known","types":["steel","ghost"]},self_item=ITEM)["state"]=="exception_applies"
    assert derive_magnet_pull_block(authority=authority,self_type=steel,self_item={"status":"known","value":"shed-shell"})["state"]=="exception_applies"
    assert aggregate_hard_blockers({"state":"insufficient_context"},magnet)["state"]=="confirmed_blocked"
