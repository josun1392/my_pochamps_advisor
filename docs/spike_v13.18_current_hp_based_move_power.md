# v13.18 Current-HP Move Power

Trusted self current/max HP powers Eruption, Water Spout, and Dragon Energy
with `max(1, floor(150 * current / maximum))`. Flail and Reversal use the
modern integer `floor(48 * current / maximum)` bracket table: `<2:200`,
`<5:150`, `<10:100`, `<17:80`, `<33:40`, otherwise `20`.

Missing or invalid exact HP never falls back to metadata power. Results are
separate from self consequence, recoil, and HP-special damage, and only
resolved power enters the existing deterministic damage path.
