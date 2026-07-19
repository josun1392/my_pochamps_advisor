# v13.11 Multi-Hit Damage and KO

PokeAPI `meta.min_hits/max_hits` is exposed on selected move metadata. Generic
fixed 2-5 hit moves use an independent-roll convolution; standard variable
2-5 uses 3/8,3/8,1/8,1/8 hit-count weights for KO counts. Exceptional moves
remain unavailable. Multi-hit is distinct from existing two-use KO and does
not integrate drain/recoil, abilities, items, per-hit events, or hit chance.
