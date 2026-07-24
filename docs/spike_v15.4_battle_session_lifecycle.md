# v15.4 Battle Session Lifecycle

MainWindow owns a monotonic instance-local sequence beginning at `ui-session-0`.
`_begin_new_battle_session()` is the explicit internal rollover boundary; it is
not called by slot selection, move selection, or advice requests. Rollover
clears Pokémon-, side-, and field-scoped confirmation state, while frozen old
request snapshots retain their original provenance. Legacy payloads remain
unchanged because session identity is used only by structured copied-input
capture.
