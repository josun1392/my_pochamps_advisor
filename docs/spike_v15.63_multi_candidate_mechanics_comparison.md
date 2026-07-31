# Multi-Candidate Mechanics Comparison Facts

Each selectable move remains an independent candidate.  The provider-safe row
now carries its existing native `mechanics_result`, separate `action_order`,
and a deterministic `comparison_facts` object:

- exact candidate identity;
- native mechanics and action-order statuses;
- bounded tags only when native evidence proves them; and
- logical evidence references (`mechanics_result` and, when present,
  `action_order`).

The facts are generated locally from the same request candidates used for the
existing damage comparison.  `immune`, KO, strictly separated native-percent
range, known-first, speed-tie, insufficient-context, and unsupported tags do
not create a score and do not alter the existing damage rank or UI slot order.
Incomplete and unsupported candidates remain unranked and retain their own
status.  Request validation regenerates the facts, so a cross-candidate ID or
tag mutation is rejected.

The provider receives this deterministic evidence but does not calculate,
modify, or return mechanics values, action order, comparison tags, or evidence
references.  Single direct-mechanics linkage is unchanged.  Validation was
offline only; no credential, provider, or network activity occurred.  A
multi-candidate actual smoke needs separate T1 approval.
