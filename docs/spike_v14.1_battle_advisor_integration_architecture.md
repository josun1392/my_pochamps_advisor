# v14.1 Battle Advisor Integration Architecture

Current production starts from UI-selected Pokémon and one selected move
(`my_selected_move`), normalizes trusted session snapshots in MainWindow and
advisor_client, builds deterministic assessments/prompt payload, crosses the
provider boundary, validates the response, and renders advice in LLMAdvicePanel.

| Layer | Input | Output | Forbidden |
|---|---|---|---|
| Snapshot collection | UI/session | trusted battle input | mechanics/inference |
| Deterministic evaluation | trusted input/metadata | assessments | recommendation prose |
| Candidate aggregation | up to four UI move slots | ordered summaries | provider/UI mutation |
| Recommendation orchestration | evidence bundle | validated recommendation | rewriting facts |
| UI presentation | validated result | advice/loading/error | raw provider output |

v14.2 candidate scope is the selected self Pokémon's available slots, maximum
four, in UI order. Current production exposes only one selected move, so v14.2
needs a small slot-to-candidate aggregation boundary. Excluded: prediction,
switching, team search, multi-turn simulation, and EV/IV/item/ability inference.

Candidate status is resolved, partial, or unavailable; evidence keeps damage,
hit/order, self effects, dynamic summary, warnings, and reasons. Partial and
unavailable candidates are retained. The bundle preserves order and forbids
untrusted inference. Recommendation statuses are resolved, insufficient_context,
no_usable_candidate, and validation_failed. A resolved choice must be in the
candidate exact-set.

Option A is recommended: LLM selects only among validated candidates while
deterministic facts remain immutable. This favors partial-context handling and
keeps deterministic pre-ranking available for later work. Provider failure
retains deterministic summaries; parser/semantic failure shows validation state
only; all-unavailable yields no fabricated recommendation. No provider, UI
orchestration, evaluator, or Turn Engine implementation is authorized here.
