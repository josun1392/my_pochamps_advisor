# v13.22 Target-HP Move Power

Crush Grip and Wring Out use `max(1, floor(120 * target current HP / target
maximum HP) + 1)` from trusted exact opponent HP only. Missing HP never falls
back to metadata power; a fainted target is not applicable.
