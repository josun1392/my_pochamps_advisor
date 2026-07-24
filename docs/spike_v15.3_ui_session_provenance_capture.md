# v15.3 UI/Session Canonical Provenance Capture

`MainWindow._build_llm_battle_input` now invokes the UI capture adapter after
existing deterministic context attachment. The adapter binds side-labelled HP,
condition, ability, stage, and event entries to the selected active slot and
Pokémon identity, with an instance-local session key. It does not invent
provenance when an active identity is unavailable. Snapshot validation remains
the consumer and retains exclusion for ambiguous legacy input.
