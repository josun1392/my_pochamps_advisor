"""Private poke-env metadata overlay for public Champions forms absent in Gen9."""

from copy import copy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from advisor.showdown_bridge import FORMAT_ID, SHOWDOWN_COMMIT


@lru_cache(maxsize=1)
def champions_data():
    from poke_env.data import GenData

    original = GenData.from_gen(9)
    private = copy(original)
    private.pokedex = original.pokedex.copy()
    source = (
        Path(__file__).resolve().parents[1]
        / "models/showdown_native_curriculum_v6/public_dex.json"
    )
    full_domain = (
        Path(__file__).resolve().parents[1]
        / "models/showdown_mc_domain_v1/public_dex.json"
    )
    if full_domain.exists():
        source = full_domain
        manifest = json.loads(
            source.with_name("manifest.json").read_text(encoding="utf-8")
        )
        if sha256(source.read_bytes()).hexdigest() != manifest.get("public_dex_sha256"):
            raise ValueError("champions_public_metadata_hash_mismatch")
    if source.exists():
        public = json.loads(source.read_text(encoding="utf-8"))
        if (
            public.get("engine_commit") != SHOWDOWN_COMMIT
            or public.get("format_id") != FORMAT_ID
        ):
            raise ValueError("champions_public_metadata_pin_mismatch")
        for identifier, entry in public["species"].items():
            if identifier not in private.pokedex:
                private.pokedex[identifier] = entry
    return private


def make_champions_battle(*args):
    from poke_env.battle import Battle

    class ChampionsBattle(Battle):
        def get_pokemon(self, *args, **kwargs):
            pokemon = super().get_pokemon(*args, **kwargs)
            pokemon._data = self._data
            return pokemon

    battle = ChampionsBattle(*args)
    battle._data = champions_data()
    return battle
