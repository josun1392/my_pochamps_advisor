# Known Move Accuracy Evidence

Each candidate now carries metadata-only `accuracy_evidence`, separate from
damage and action-order: canonical numeric accuracy, always-hits, missing
metadata, or unsupported dynamic accuracy. It never calculates final hit
probability or treats accuracy 100 as always-hits. Comparison tags are emitted
only when multiple canonical numeric values are known; ranking is unchanged.
Selected-candidate presentation renders only bounded accuracy text. Offline only.
