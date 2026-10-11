"""Offline-only Qt worker for a frozen native evaluation job."""
from copy import deepcopy
from PySide6.QtCore import QObject, QThread, Signal, Slot
from llm.advisor_showdown_shadow import evaluate_current_showdown_shadow
from llm.advisor_showdown_strategy_evaluation import experimental_ranking


class NativeStrategyEvaluationWorker(QObject):
    completed = Signal(object)

    def __init__(self, *, generation, job, explanation, bridge):
        super().__init__()
        self.generation, self.job = generation, deepcopy(job)
        self.explanation, self.bridge = deepcopy(explanation), bridge

    @Slot()
    def run(self):
        explanation = self.explanation
        if not QThread.currentThread().isInterruptionRequested():
            try:
                explanation["sampled_simulation"] = evaluate_current_showdown_shadow(
                    runtime_snapshot=self.job["runtime_snapshot"], selection=self.job["selection"],
                    context=self.job["context"], bridge=self.bridge)
                experiment = experimental_ranking(evidence=explanation["sampled_simulation"], explanation=explanation,
                    enabled=self.job["experimental_ranking"])
                if experiment is not None: explanation["experimental_ranking"] = experiment
            except Exception:
                # Infrastructure failure keeps the previously captured default explanation.
                explanation["sampled_simulation"].update(status="unavailable", reason="native_evaluation_failed")
        else:
            explanation["sampled_simulation"].update(status="unavailable", reason="native_evaluation_cancelled")
        self.completed.emit({"generation": self.generation, "explanation": explanation})
