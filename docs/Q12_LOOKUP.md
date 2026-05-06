# Q12 lookup table — verified against @smogon/calc@0.11.0 gen789.ts
# Last audit: 2026-05-06

BP_MOD_5325_GROUP = {  # ×1.30 to base power
    "tough-claws":   {"flag": "contact"},
    "sheer-force":   {"condition": "has_secondaries"},
    "punk-rock":     {"flag": "sound"},          # offensive only
    "technician":    {"condition": "bp <= 60"},
    "strong-jaw":    {"flag": "bite"},
    "mega-launcher": {"flag": "pulse"},
}

BP_MOD_4915_GROUP = {  # ×1.20 to base power
    "iron-fist": {"flag": "punch"},
    "reckless":  {"condition": "is_recoil_or_crash"},
}

AT_MOD_GEN9 = {  # attack-stat multipliers
    "transistor": {"q12": 5325, "type": "electric"},  # Gen 9 NERFED from 6144
    # huge-power, pure-power → q12: 8192 (×2.0), no condition
}

FINAL_MOD_HALF = {  # ×0.50 defensive
    "punk-rock":  {"flag": "sound"},     # defender side
    "ice-scales": {"category": "Special"},
}
