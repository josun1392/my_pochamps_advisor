# Current weather and active-ability authority

The reducer begins with unknown global weather and unknown current ability for
each Pokémon identity.  Explicit trusted observations may replace them through
the lifecycle, replay, reducer, and detached runtime snapshot path.

`current_weather_observed` records only one exact current weather value:
`none`, `sun`, `rain`, `sandstorm`, or `snow`.  It is global/session owned and
requires a positive trusted turn number.  `none` is a trusted deterministically
not-Sandstorm state; absent observation remains unknown.

`current_ability_observed` records one exact current ability for a matching
side, slot, and Pokémon identity.  It never derives an ability from species or
an ability pool.  A replacement active identity starts unknown and cannot
inherit the outgoing Pokémon's ability.  Later snapshots are detached from
later reducer replacements.

The existing reducer-owned held-item field remains the only item authority
projected at this seam.  This unit does not activate abilities or items, infer
weather, model weather duration, or resolve Sandstorm residual damage.
