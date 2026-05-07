# Spike v0.5 Design — LLM Advice Panel

## 1. Goal

Add a minimal PySide6 UI integration for the Gemini pre-computed injection spike. The Q12 damage and probability engines remain the deterministic input source. The LLM is only the explanation/recommendation layer; it does not replace `advisor/damage/` or `advisor/probability/`.

v0.5 target: one manual button click produces one LLM recommendation from the
existing hardcoded Mega Kangaskhan vs Garchomp spike and displays token/cost status.

## 2. Confirmed Decisions

- LLM calls use a `QThread` + `QObject` worker. Synchronous UI calls are forbidden.
- New widget file: `ui/widgets/llm_advice_panel.py`.
- Existing `AnalysisPanel` stays. `AnalysisPanel` and `LLMAdvicePanel` coexist.
- MVP layout ratio:
  - `layout.addWidget(self.analysis_panel, 1)`
  - `layout.addWidget(self.llm_advice_panel, 1)`
- Trigger is manual only. Button text: `이번 턴 추천 받기`.
- Token/cost summary appears in `MainWindow.statusBar()` by default.
- Fallback cost display is a small QLabel inside `LLMAdvicePanel`.
- Cost text must not be mixed into the recommendation `QTextEdit`.
- No `QSplitter` in v0.5. Consider it for v0.6.
- No timestamp in v0.5 status messages. Consider it for v0.6.

## 3. UI Placement

Place `LLMAdvicePanel` inside the central AI analysis column, below the existing `AnalysisPanel`. Do not alter `analysis_panel.py`.

The center column will show: title label, Pokemon search box, existing `AnalysisPanel`, and new `LLMAdvicePanel`.

## 4. Class Design

Design-level pseudo-signatures only:

```python
class LLMAdvicePanel(QFrame):
    advice_requested = Signal()

    def set_running(self, is_running: bool) -> None: ...
    def set_advice_text(self, text: str) -> None: ...
    def set_error(self, message: str) -> None: ...
    def clear(self) -> None: ...
```

Internal widgets: `QPushButton("이번 턴 추천 받기")`, read-only `QTextEdit` or `QPlainTextEdit`, and a small `QLabel` for fallback token/cost status.

```python
class LLMAdviceWorker(QObject):
    finished = Signal(str, dict)
    failed = Signal(str)
    status = Signal(str)  # optional

    def run(self) -> None: ...
```

## 5. Worker Thread Design

- Worker never touches UI objects directly.
- Worker emits signals only.
- UI updates happen on the main thread.
- While running:
  - Button disabled
  - Advice text set to `분석 중...`
  - Status bar set to `Analyzing...`
- Timeout uses the existing internal `requests.post(..., timeout=60)` behavior in `call_gemini()`.
- v0.5 has no cancel button.

## 6. Signal / Slot Contract

Flow:
1. Button click
2. `LLMAdvicePanel.advice_requested` emitted
3. `AnalysisColumn` or `MainWindow` creates `QThread` + `LLMAdviceWorker`
4. `QThread.start()`
5. Worker `run()`
6. Success: `finished(recommendation, usage_summary)`
7. Failure: `failed(error_message)`
8. UI thread updates text/status bar
9. Button re-enabled
10. Thread/worker cleaned up with `deleteLater()`

Recommended ownership: `MainWindow` owns status-bar updates and worker lifecycle.
`LLMAdvicePanel` owns only its button/text/fallback label.

## 7. LLM Call Flow

Reuse the current spike path for MVP:

1. `collect_battle_data()`
2. `build_prompt(data)`
3. `call_gemini(prompt, model)`
4. `TokenLogger.log_call(...)`
5. emit recommendation text
6. emit token/cost summary

Current callable functions in `scripts/spike_advisor.py`:

```python
collect_battle_data() -> dict[str, Any]
build_prompt(data: dict[str, Any]) -> str
call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]
```

v0.5 recommendation: minimal import from `scripts.spike_advisor` is acceptable. If the UI code starts to grow, extract a thin helper later:

```python
run_spike_advice(model: str = DEFAULT_MODEL) -> tuple[str, dict, dict]
```

Do not modify `advisor/damage/`.

## 8. Error Handling

- Missing `GEMINI_API_KEY` / `GOOGLE_API_KEY`:
  - `API key가 설정되지 않았습니다.`
- HTTP 4xx/5xx:
  - `Gemini API 오류: status code ...`
- Timeout:
  - `요청 시간이 초과되었습니다.`
- Unexpected response JSON:
  - `LLM 응답 형식을 읽지 못했습니다.`
- `TokenLogger` failure:
  - Recommendation still displays.
  - Status bar says cost logging failed.
- Any other exception:
  - App must not crash.
  - Show a friendly failure message and re-enable the button.

## 9. MainWindow Integration Plan

Patch-level plan only:

```python
from ui.widgets.llm_advice_panel import LLMAdvicePanel
```

Inside `AnalysisColumn.__init__`:

```python
self.analysis_panel = AnalysisPanel()
self.llm_advice_panel = LLMAdvicePanel()
layout.addWidget(title_label)
layout.addWidget(self.search_box)
layout.addWidget(self.analysis_panel, 1)
layout.addWidget(self.llm_advice_panel, 1)
```

Status-bar recommendation: `MainWindow` provides a callback or connects to `AnalysisColumn` signals. `MainWindow.statusBar().showMessage(...)` owns status updates. `AnalysisColumn` should not need to know token pricing details.

## 10. TokenLogger / Status Bar Plan

Primary display: `MainWindow.statusBar()`. Fallback display: `LLMAdvicePanel` bottom QLabel. Examples:

- `Analyzing...`
- `Done | input 1960 / output 189 | $0.0010605`
- `Failed | API key missing`
- `Done | recommendation shown | cost logging failed`

The recommendation text area contains only the LLM recommendation.

## 11. Manual Verification Scenarios

v0.5 prioritizes manual verification over automated Qt tests:

1. Run the app.
2. Confirm central AI analysis column shows both `AnalysisPanel` and `LLMAdvicePanel`.
3. Click `이번 턴 추천 받기`.
4. Confirm the button is disabled and `분석 중...` appears.
5. Confirm successful LLM answer appears in the text area.
6. Confirm status bar shows input/output/cost.
7. Remove API key and confirm friendly missing-key error.
8. Confirm button is re-enabled after failure.
9. Confirm UI does not freeze during the LLM call.
10. Run pytest and keep the existing 613 passing default suite.

## 12. Out of Scope

- Actual implementation in this design-only task
- Automatic LLM calls
- Streaming responses
- Cancel/retry advanced controls
- Critic loop / self-review agent / second-pass judge; deferred as premature complexity, not permanently banned
- Minimax reintroduction
- Dual Minimax + LLM toggle
- PoChamps format override implementation
- `advisor/damage/` changes
- Q12 damage engine changes
- Team builder completion
- Full battle-state modeling
- Large network/API refactor
- `asyncio` / `httpx` migration
- Gemini SDK migration
- `QSplitter`
- Status-bar timestamp

## 13. Rollback Plan

If the UI spike causes trouble:

1. Remove `LLMAdvicePanel` import from `main_window.py`.
2. Remove `self.llm_advice_panel = LLMAdvicePanel()`.
3. Remove `layout.addWidget(self.llm_advice_panel, 1)`.
4. Leave or delete `ui/widgets/llm_advice_panel.py`.
5. Keep `docs/spike_v0.5_design.md`; it is safe as historical design context.
6. Re-run pytest.
7. The UI returns to the existing `AnalysisPanel`-only center column.
