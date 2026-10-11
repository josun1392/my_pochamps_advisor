"""Curated broad hypothetical sets; native M-C TeamValidator is authoritative.

These are experimental coverage fixtures, not usage statistics or optimal sets.
The species-disjoint pool is reserved for fresh final generalization evaluation.
"""

# species | ability | four moves | investment | optional Mega stone
_TRAIN = """
Blastoise|Torrent|Surf,Ice Beam,Dark Pulse,Protect|spa|Blastoisinite
Gardevoir|Trace|Moonblast,Psychic,Thunderbolt,Calm Mind|spa|Gardevoirite
Metagross|Clear Body|Meteor Mash,Zen Headbutt,Bullet Punch,Earthquake|atk|Metagrossite
Sylveon|Pixilate|Hyper Voice,Shadow Ball,Calm Mind,Protect|spa|
Salamence|Intimidate|Dragon Claw,Earthquake,Roost,Dragon Dance|atk|Salamencite
Swampert|Torrent|Waterfall,Earthquake,Ice Punch,Stealth Rock|atk|Swampertite
Corviknight|Pressure|Brave Bird,Body Press,Roost,Iron Defense|def|
Toxapex|Regenerator|Surf,Toxic,Recover,Haze|def|
Hippowdon|Sand Stream|Earthquake,Stealth Rock,Slack Off,Whirlwind|def|
Clefable|Magic Guard|Moonblast,Calm Mind,Moonlight,Thunder Wave|spd|
Chesnaught|Bulletproof|Seed Bomb,Drain Punch,Spikes,Synthesis|def|
Skarmory|Sturdy|Brave Bird,Spikes,Roost,Whirlwind|def|
Umbreon|Synchronize|Foul Play,Wish,Protect,Toxic|spd|
Slowbro|Regenerator|Surf,Psychic,Slack Off,Thunder Wave|def|Slowbronite
Arcanine|Intimidate|Flare Blitz,Extreme Speed,Will-O-Wisp,Morning Sun|atk|
Incineroar|Intimidate|Flare Blitz,Darkest Lariat,Parting Shot,Fake Out|atk|
Meowscarada|Protean|Flower Trick,Knock Off,U-turn,Spikes|atk|
Dragapult|Infiltrator|Dragon Darts,Phantom Force,U-turn,Dragon Dance|atk|
Kingambit|Defiant|Kowtow Cleave,Sucker Punch,Iron Head,Swords Dance|atk|
Gholdengo|Good as Gold|Make It Rain,Shadow Ball,Recover,Nasty Plot|spa|
Volcarona|Flame Body|Fiery Dance,Bug Buzz,Giga Drain,Quiver Dance|spa|
Pelipper|Drizzle|Surf,Hurricane,U-turn,Roost|spa|
Excadrill|Mold Breaker|Earthquake,Iron Head,Rapid Spin,Swords Dance|atk|
Serperior|Contrary|Leaf Storm,Dragon Pulse,Glare,Synthesis|spa|
Mimikyu|Disguise|Play Rough,Shadow Sneak,Shadow Claw,Swords Dance|atk|
Garganacl|Purifying Salt|Salt Cure,Body Press,Recover,Iron Defense|def|
Skeledirge|Unaware|Torch Song,Shadow Ball,Will-O-Wisp,Slack Off|def|
Rillaboom|Grassy Surge|Grassy Glide,Wood Hammer,Knock Off,U-turn|atk|
Annihilape|Defiant|Rage Fist,Drain Punch,Bulk Up,Taunt|atk|
Gliscor|Poison Heal|Earthquake,Knock Off,Protect,Toxic|def|
"""
_UNSEEN = """
Primarina|Torrent|Moonblast,Surf,Ice Beam,Calm Mind|spa|
Hatterene|Magic Bounce|Psychic,Dazzling Gleam,Calm Mind,Draining Kiss|spa|
Milotic|Competitive|Surf,Ice Beam,Recover,Haze|spd|
Hydreigon|Levitate|Dark Pulse,Dragon Pulse,Flamethrower,Nasty Plot|spa|
Kommo-o|Bulletproof|Drain Punch,Dragon Claw,Bulk Up,Protect|atk|
Forretress|Sturdy|Gyro Ball,Volt Switch,Spikes,Rapid Spin|def|
Chandelure|Flash Fire|Shadow Ball,Flamethrower,Energy Ball,Will-O-Wisp|spa|
Whimsicott|Prankster|Moonblast,Energy Ball,Leech Seed,Encore|spa|
Talonflame|Gale Wings|Brave Bird,Flare Blitz,Roost,Will-O-Wisp|atk|
Vaporeon|Water Absorb|Surf,Ice Beam,Wish,Protect|spd|
Goodra|Sap Sipper|Dragon Pulse,Flamethrower,Thunderbolt,Protect|spd|
Azumarill|Huge Power|Play Rough,Liquidation,Aqua Jet,Belly Drum|atk|
Sableye|Prankster|Foul Play,Will-O-Wisp,Recover,Taunt|def|Sablenite
Alakazam|Magic Guard|Psychic,Shadow Ball,Focus Blast,Encore|spa|Alakazite
"""


def _parse(text):
    return [
        (s, a, moves.split(","), investment, stone)
        for line in text.strip().splitlines()
        for s, a, moves, investment, stone in [line.split("|")]
    ]


BROAD_TRAIN = _parse(_TRAIN)
BROAD_UNSEEN = _parse(_UNSEEN)
