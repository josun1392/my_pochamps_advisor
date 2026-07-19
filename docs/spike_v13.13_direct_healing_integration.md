# v13.13 Direct Healing

PokeAPI `meta.healing` is mapped into selected move metadata. Generic immediate
self healing floors max HP percentage then caps at missing HP. Conditional,
weather, delayed, status, target-dependent, and multi-target healing moves are
unavailable; direct healing remains separate from drain, damage, and hit chance.
