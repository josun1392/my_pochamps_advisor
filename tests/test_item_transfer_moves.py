from advisor.canonical_item_transfer_moves import resolve_canonical_item_transfer_move
from llm.advisor_detached_item_transfer_after_hit import materialize_detached_item_transfer_after_hit
def test_catalog_and_transfer():
 assert resolve_canonical_item_transfer_move(move={"move_id":"thief"})["effect"]["base_power"]==60
 assert resolve_canonical_item_transfer_move(move={"move_id":"covet"})["effect"]["type"]=="normal"
 a={"status":"resolved","move_id":"thief","user":{"side":"self"},"target":{"side":"opponent"},"user_item_state":"known_absent","user_item_before":None,"target_item_state":"known_present","target_item_before":"black-belt","removable":True,"sticky_hold":False}
 l={"leaf_id":"hit","hit_state":"hit","provenance":{"move_id":"thief","attacker":{"side":"self"},"target":{"side":"opponent"}},"consequences":{"damage":1,"self_fainted":False,"source_hit_context":{"target_routing":"target"}}}
 r=materialize_detached_item_transfer_after_hit(authority=a,source_leaf=l)
 assert (r["outcome"],r["user_item_after"],r["target_item_after"])==("transferred","black-belt",None)
