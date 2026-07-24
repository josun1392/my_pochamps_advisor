# v15.5 New-Battle Lifecycle Hook

No existing UI new-match action was found. `MainWindow.begin_new_battle()` is
the application-level lifecycle API for future UI wiring and delegates exactly
once to the v15.4 rollover helper. It adds no button and does not run for slot,
move, or advice actions.
