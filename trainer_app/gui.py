"""Responsive separate Qt desktop frontend; heavy learning stays out of the GUI."""

import html
import json
from pathlib import Path
from time import time

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QFileDialog,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QMessageBox,
    QHeaderView,
)

from advisor.learning_resources import atomic_json
from trainer_app.runtime import (
    data_root,
    safe_user_path,
    default_engine,
    model_choices,
    make_config,
    new_run,
    launch_worker,
    stop_run,
    snapshot,
    read_json,
    export_best,
    busy_run,
)


class Trend(QWidget):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.setMinimumHeight(145)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor("#14202e"))
        p.setPen(QColor("#9fb2c8"))
        p.drawText(16, 22, "Validation sample win fraction — exact probability 아님")
        for i in range(5):
            y = 40 + (h - 62) * i / 4
            p.setPen(QColor("#2d3b4c"))
            p.drawLine(45, int(y), w - 15, int(y))
            p.setPen(QColor("#9fb2c8"))
            p.drawText(6, int(y) + 4, f"{100 - i * 25}%")
        if not self.rows:
            return
        base = self.rows[0]["steps"]
        maximum = max(1, max(r["steps"] - base for r in self.rows))
        points = [
            (
                45 + (w - 62) * (r["steps"] - base) / maximum,
                40 + (h - 62) * (1 - r["score"]),
            )
            for r in self.rows
        ]
        p.setPen(QPen(QColor("#4cb5ed"), 2))
        for a, b in zip(points, points[1:]):
            p.drawLine(int(a[0]), int(a[1]), int(b[0]), int(b[1]))
        for x, y in points:
            p.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)


class TrainerWindow(QMainWindow):
    def __init__(self, root=None, smoke_plan=None):
        super().__init__()
        self.setWindowTitle("PokeAdvice AI Trainer")
        self.resize(1160, 850)
        self.root = safe_user_path(root or data_root())
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.root / "settings.json"
        self.run_path = None
        self.smoke = read_json(smoke_plan) if smoke_plan else None
        self.smoke_started = time()
        self.smoke_phase = "start"
        self.smoke_resume_transitions = 0
        self.setStyleSheet(
            'QWidget {background:#101a26;color:#e7eef7;font:10pt "Segoe UI";} QLineEdit,QSpinBox,QComboBox,QTextEdit,QTableWidget {background:#1a293a;border:1px solid #33455b;border-radius:4px;padding:4px;} QPushButton {background:#263c53;border:1px solid #42617d;border-radius:5px;padding:8px 16px;} QPushButton:hover {background:#345976;} QPushButton:disabled {color:#65788d;} QTabBar::tab {padding:8px 18px;}'
        )
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        title = QLabel("PokeAdvice  •  AI Trainer")
        title.setStyleSheet("font-size:22pt;font-weight:600;")
        layout.addWidget(title)
        description = QLabel(
            "독립 CPU 학습 · native M-C · 공개 관측 · 실험 모델 전용  |  기본 배틀 추천은 변경하지 않습니다."
        )
        layout.addWidget(description)
        self.status = QLabel("idle")
        self.status.setStyleSheet("font-size:14pt;color:#54c4ef;")
        layout.addWidget(self.status)
        settings = QWidget()
        self.settings_panel = settings
        self.settings_toggle = QPushButton("학습 설정 접기 / 펼치기")
        self.settings_toggle.clicked.connect(
            lambda: settings.setVisible(not settings.isVisible())
        )
        layout.addWidget(self.settings_toggle)
        form = QFormLayout(settings)
        self.domain = QComboBox()
        self.domain.addItem("전체 M-C — 231종, 팀/구성 평가", "full_mc")
        self.domain.addItem(
            "종 분리 연구 — V7 train168 / validation12", "species_disjoint"
        )
        form.addRow("학습 도메인", self.domain)
        self.initial = QComboBox()
        self.initial.addItem("Fresh — 새 actor/critic 초기화", "")
        for name, path in model_choices().items():
            self.initial.addItem(name + " — 명시적 full-catalog 호환 모델", str(path))
        self.initial.setCurrentIndex(1)
        form.addRow("시작 체크포인트", self.initial)
        self.model_path = QLineEdit()
        browse = QPushButton("모델 선택")
        browse.clicked.connect(self.browse_model)
        row = QHBoxLayout()
        row.addWidget(self.model_path)
        row.addWidget(browse)
        form.addRow("직접 선택 (ZIP + JSON)", row)
        self.optimizer = QCheckBox("warm-start에서 optimizer를 새로 초기화")
        form.addRow("", self.optimizer)
        self.engine = QLineEdit(str(default_engine()))
        button = QPushButton("폴더 선택")
        button.clicked.connect(self.browse_engine)
        row = QHBoxLayout()
        row.addWidget(self.engine)
        row.addWidget(button)
        form.addRow("Showdown 런타임", row)
        self.preset = QComboBox()
        self.preset.addItems(
            ["Dedicated CPU — 8 workers", "Interactive CPU — 2 workers"]
        )
        self.preset.currentIndexChanged.connect(self.set_preset)
        form.addRow("CPU preset", self.preset)
        self.minutes = self.spin(1, 360, 120)
        self.steps = self.spin(1024, 1048576, 262144, 1024)
        self.seed = self.spin(1, 999999, 51061)
        self.envs = self.spin(1, 8, 8)
        self.threads = self.spin(1, 8, 4)
        self.cpu = self.spin(1, 75, 50)
        self.memory = self.spin(1024, 16384, 12288, 1024)
        self.interval = self.spin(1024, 65536, 8192, 1024)
        self.cases = self.spin(1, 64, 32)
        self.patience = self.spin(1, 12, 4)
        limits = QHBoxLayout()
        for name, control in [
            ("최대 분", self.minutes),
            ("PPO 전이", self.steps),
            ("seed", self.seed),
        ]:
            limits.addWidget(QLabel(name))
            limits.addWidget(control)
        form.addRow("학습 예산", limits)
        limits = QHBoxLayout()
        for name, control in [
            ("workers", self.envs),
            ("tensor threads", self.threads),
            ("CPU %", self.cpu),
            ("RAM MiB", self.memory),
        ]:
            limits.addWidget(QLabel(name))
            limits.addWidget(control)
        form.addRow("프로세스 한도", limits)
        limits = QHBoxLayout()
        for name, control in [
            ("평가 간격", self.interval),
            ("cases/rival", self.cases),
            ("plateau", self.patience),
        ]:
            limits.addWidget(QLabel(name))
            limits.addWidget(control)
        form.addRow("고정 validation", limits)
        self.boundary = QLabel(
            "Final holdouts는 자동 선택에 사용하지 않습니다. GPU: CPU 전용 배포에 포함되지 않습니다.\n종 분리 연구에서 역사적 warm 모델은 과거 종 노출 가능성이 있습니다. Bring-6/pick-3 선택은 coordinator fixture입니다."
        )
        self.boundary.setWordWrap(True)
        form.addRow("", self.boundary)
        layout.addWidget(settings)
        buttons = QHBoxLayout()
        self.start = QPushButton("학습 시작")
        self.stop = QPushButton("안전 STOP")
        self.resume = QPushButton("체크포인트 재개")
        self.evaluate = QPushButton("Validation 재평가")
        self.open_run = QPushButton("기존 실행 열기")
        for b in (self.start, self.stop, self.resume, self.evaluate, self.open_run):
            buttons.addWidget(b)
        layout.addLayout(buttons)
        self.start.clicked.connect(self.start_training)
        self.stop.clicked.connect(self.request_stop)
        self.resume.clicked.connect(self.resume_training)
        self.evaluate.clicked.connect(self.evaluate_model)
        self.open_run.clicked.connect(self.choose_run)
        self.progress = QLabel("PPO 0  |  종료 배틀 0")
        self.progress.setStyleSheet("font-size:13pt;")
        layout.addWidget(self.progress)
        self.resources = QLabel("")
        layout.addWidget(self.resources)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        metrics = QWidget()
        metrics_layout = QVBoxLayout(metrics)
        self.trend = Trend()
        metrics_layout.addWidget(self.trend)
        self.checkpoints = QTableWidget(0, 5)
        self.checkpoints.setHorizontalHeaderLabels(
            ["stage", "steps (선행 학습 포함)", "wins/n", "sample %", "truncations"]
        )
        self.checkpoints.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        metrics_layout.addWidget(self.checkpoints)
        self.tabs.addTab(metrics, "학습 / 검증 추세")
        self.opponents = QTableWidget(0, 5)
        self.opponents.setHorizontalHeaderLabels(
            ["opponent", "W / L", "n", "sample win %", "Wilson 95% (표본)"]
        )
        self.opponents.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabs.addTab(self.opponents, "상대별 검증")
        self.coverage = QTextEdit()
        self.coverage.setReadOnly(True)
        self.tabs.addTab(self.coverage, "종 / 형태 / 공개 행동")
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.tabs.addTab(self.logs, "진단")
        self.ppo = QTextEdit()
        self.ppo.setReadOnly(True)
        self.tabs.addTab(self.ppo, "PPO 학습 지표")
        self.best_label = QLabel("검증 best: 아직 없음")
        self.best_label.setWordWrap(True)
        layout.addWidget(self.best_label)
        buttons = QHBoxLayout()
        folder = QPushButton("실행 / 모델 폴더")
        folder.clicked.connect(self.show_folder)
        report = QPushButton("평가 보고서")
        report.clicked.connect(self.show_report)
        export = QPushButton("Best 모델 내보내기")
        export.clicked.connect(self.export_model)
        for b in (folder, report, export):
            buttons.addWidget(b)
        layout.addLayout(buttons)
        layout.addWidget(
            QLabel(
                "GUI를 닫아도 독립 worker는 예산 내에서 계속 실행됩니다. 중지는 안전 STOP을 사용하세요. 토큰/provider 호출 없음."
            )
        )
        previous = read_json(self.settings_path)
        if previous.get("last_run") and Path(previous["last_run"]).exists():
            self.run_path = Path(previous["last_run"])
        if previous.get("engine"):
            self.engine.setText(previous["engine"])
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()
        if self.smoke:
            QTimer.singleShot(300, self.smoke_tick)

    @staticmethod
    def spin(low, high, value, step=1):
        w = QSpinBox()
        w.setRange(low, high)
        w.setValue(value)
        w.setSingleStep(step)
        return w

    def set_preset(self, index):
        for widget, value in (
            (self.envs, 2 if index else 8),
            (self.threads, 1 if index else 4),
            (self.cpu, 25 if index else 50),
            (self.memory, 4096 if index else 12288),
        ):
            widget.setValue(value)

    def browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Trusted local model checkpoint", "", "Model (*.zip)"
        )
        if path:
            self.model_path.setText(path)

    def browse_engine(self):
        path = QFileDialog.getExistingDirectory(
            self, "Pinned Showdown checkout", self.engine.text()
        )
        if path:
            self.engine.setText(path)

    def options(self):
        return {
            "domain": self.domain.currentData(),
            "initial_model": self.model_path.text().strip()
            or self.initial.currentData(),
            "fresh_optimizer": self.optimizer.isChecked(),
            "runtime_seconds": self.minutes.value() * 60,
            "steps": self.steps.value(),
            "seed": self.seed.value(),
            "envs": self.envs.value(),
            "cpu_threads": self.threads.value(),
            "cpu_percent": self.cpu.value(),
            "memory_mib": self.memory.value(),
            "checkpoint_steps": self.interval.value(),
            "validation_cases": self.cases.value(),
            "plateau_patience": self.patience.value(),
        }

    def error(self, error):
        self.status.setText("failed — " + str(error))
        if self.smoke:
            atomic_json(self.root / "smoke_failure.json", {"message": str(error)})
            self.close()
        else:
            QMessageBox.warning(self, "실행 오류", str(error))

    def start_training(self):
        try:
            if busy_run(self.root / "runs"):
                raise ValueError(
                    "이미 실행 중인 worker가 있습니다. 기존 실행을 열어 STOP하세요."
                )
            config = make_config(self.options(), self.engine.text())
            self.run_path = new_run(self.root / "runs", config)
            self.save_settings()
            launch_worker(self.run_path)
            self.settings_panel.setVisible(False)
            self.refresh()
        except (ValueError, OSError) as error:
            self.error(error)

    def save_settings(self):
        atomic_json(
            self.settings_path,
            {
                "last_run": str(self.run_path) if self.run_path else None,
                "engine": self.engine.text(),
            },
        )

    def request_stop(self):
        if self.run_path:
            stop_run(self.run_path)
            self.refresh()

    def resume_training(self):
        try:
            launch_worker(self.run_path, resume=True)
            self.refresh()
        except (ValueError, OSError) as error:
            self.error(error)

    def evaluate_model(self):
        try:
            launch_worker(self.run_path, evaluate=True)
            self.refresh()
        except (ValueError, OSError) as error:
            self.error(error)

    def choose_run(self):
        path = QFileDialog.getExistingDirectory(
            self, "Desktop run folder", str(self.root / "runs")
        )
        if path:
            if not (Path(path) / "desktop.json").exists():
                self.error(ValueError("데스크톱 앱에서 생성한 실행 폴더가 아닙니다."))
                return
            self.run_path = Path(path)
            self.save_settings()
            self.refresh()

    def refresh(self):
        if not self.run_path:
            self.stop.setEnabled(False)
            self.resume.setEnabled(False)
            self.evaluate.setEnabled(False)
            return
        try:
            view = snapshot(self.run_path)
        except (ValueError, OSError) as error:
            self.status.setText("failed — " + str(error))
            return
        state = view["state"]
        alive = view["alive"]
        self.settings_panel.setEnabled(not alive)
        self.status.setText(view["phase"] + "  |  " + self.run_path.name)
        self.start.setEnabled(not alive)
        self.open_run.setEnabled(not alive)
        self.stop.setEnabled(alive)
        self.resume.setEnabled(
            not alive
            and bool(state.get("latest"))
            and state.get("status") != "complete"
        )
        self.evaluate.setEnabled(not alive and bool(state.get("best")))
        self.progress.setText(
            f"PPO {view['transitions']:,}  |  종료 배틀 {view['battles']:,}  |  완료 rollout 전이 {state.get('trained_rollout_transitions', 0):,}"
        )
        resource = view["resources"]
        self.resources.setText(
            f"Peak job RAM {resource.get('peak_job_memory_bytes', 0) / 1024**3:.2f} GiB  |  CPU tree {resource.get('tree_cpu_seconds', 0):.1f}s  |  processes {resource.get('active_processes', 0)}  |  validation-best {state.get('best_score', -1):.3f}  |  plateau {state.get('plateau', 0)}"
        )
        rows = state.get("evaluations", [])
        self.trend.rows = rows
        self.trend.update()
        self.checkpoints.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(
                (
                    row["stage"],
                    row["steps"],
                    f"{row['wins']}/{row['n']}",
                    f"{row['score'] * 100:.1f}",
                    row["truncated"],
                )
            ):
                self.checkpoints.setItem(i, j, QTableWidgetItem(str(value)))
        report = read_json(self.run_path / "manual_validation.json")
        if not report and rows:
            report = read_json(Path(rows[-1]["checkpoint"]).parent / "validation.json")
        summaries = [r for r in report.get("summaries", []) if r["opponent"] != "all"]
        self.opponents.setRowCount(len(summaries))
        for i, row in enumerate(summaries):
            low, high = row["wilson_95"]
            for j, value in enumerate(
                (
                    row["opponent"],
                    f"{row['wins']} / {row['losses']}",
                    row["n"],
                    f"{row['win_fraction'] * 100:.1f}%",
                    f"{low * 100:.1f}–{high * 100:.1f}%",
                )
            ):
                self.opponents.setItem(i, j, QTableWidgetItem(str(value)))
        text = [
            "실제 episode reset 구성 집계. 상대 hidden 구성은 actor/critic 관측으로 전달되지 않습니다.",
            "시작 형태 != 모든 변신 실행; moves 구성 != 모든 기술 실행.",
            "코디네이터 bring6/pick3, final holdout 자동 선택 없음.",
            "",
        ]
        text += [
            f"{k}: {len(v)} distinct"
            for k, v in state.get("sampled_domain_coverage", {}).items()
        ]
        text += [
            "",
            "정책이 선택한 공개 행동의 거친 분류 (전략 우위 label 아님):",
            json.dumps(state.get("public_tactical_action_counts", {}), indent=2),
        ]
        self.coverage.setPlainText("\n".join(text))
        failed = (
            read_json(self.run_path / "desktop_failure.json")
            if view["phase"] == "failed"
            else {}
        )
        log = self.run_path / "worker.log"
        if log.exists():
            with log.open("rb") as f:
                f.seek(max(0, log.stat().st_size - 8000))
                content = f.read().decode("utf-8", errors="replace")
        else:
            content = "준비 중..."
        self.logs.setPlainText((failed.get("message", "") + "\n" + content)[-10000:])
        metrics = []
        # Saved models contain existing PPO diagnostics; no extra trainer metrics
        # or learning signals are introduced by this presentation.
        for row in rows[-32:]:
            metadata = read_json(Path(row["checkpoint"]).with_suffix(".json"))
            detail = metadata.get("training_metrics", {})
            if detail:
                metrics.append({"steps": row["steps"], **detail})
        self.ppo.setPlainText(json.dumps(metrics, indent=2))
        self.best_label.setText(
            "검증 best: "
            + str(state.get("best") or "아직 없음")
            + "\n현재: "
            + str(
                state.get("latest") or (rows[-1]["checkpoint"] if rows else "아직 없음")
            )
        )
        atomic_json(
            self.root / "gui_status.json",
            {
                "phase": view["phase"],
                "run": str(self.run_path),
                "transitions": view["transitions"],
                "battles": view["battles"],
                "heartbeat_time": time(),
                "responsive_tick": True,
            },
        )

    def show_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.run_path or self.root)))

    def show_report(self):
        if not self.run_path:
            return
        state = read_json(self.run_path / "state.json")
        lines = [
            '<html><meta charset="utf-8"><body><h1>PokeAdvice AI Trainer</h1><p>Validation samples, not exact win probabilities. Production recommendation unchanged.</p>'
        ]
        lines.append(
            "<pre>"
            + html.escape(
                json.dumps(
                    {
                        k: state.get(k)
                        for k in (
                            "transitions",
                            "completed_battles",
                            "best",
                            "best_score",
                            "episode_outcomes",
                            "public_tactical_action_counts",
                        )
                    },
                    indent=2,
                )
            )
            + "</pre>"
        )
        for row in state.get("evaluations", []):
            report = read_json(Path(row["checkpoint"]).parent / "validation.json")
            lines.append(
                "<h2>"
                + html.escape(row["stage"] + " " + str(row["steps"]))
                + "</h2><pre>"
                + html.escape(json.dumps(report.get("summaries", []), indent=2))
                + "</pre>"
            )
        path = self.run_path / "report.html"
        path.write_text("\n".join(lines) + "</body></html>", encoding="utf-8")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def export_model(self):
        if not self.run_path:
            return
        destination = QFileDialog.getExistingDirectory(self, "Export parent folder")
        if destination:
            try:
                path = export_best(
                    self.run_path, Path(destination) / ("best_" + self.run_path.name)
                )
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            except (ValueError, OSError) as error:
                self.error(error)

    def smoke_tick(self):
        try:
            if time() - self.smoke_started > self.smoke.get("deadline", 180):
                raise RuntimeError("Bounded GUI smoke deadline exceeded")
            options = self.smoke.get("options", {})
            if self.smoke_phase == "start":
                if self.smoke.get("resume_existing"):
                    self.run_path = Path(self.smoke["resume_existing"])
                    self.smoke_resume_transitions = read_json(
                        self.run_path / "state.json"
                    ).get("transitions", 0)
                    self.resume.click()
                    self.smoke_phase = "resume"
                elif self.smoke.get("attach_stop"):
                    self.run_path = Path(self.smoke["attach_stop"])
                    self.refresh()
                    self.request_stop()
                    self.smoke_phase = "stopping"
                elif self.smoke.get("evaluate_existing"):
                    self.run_path = Path(self.smoke["evaluate_existing"])
                    self.refresh()
                    self.evaluate.click()
                    self.smoke_phase = "evaluation"
                else:
                    for key, widget in [
                        ("envs", self.envs),
                        ("steps", self.steps),
                        ("seed", self.seed),
                        ("checkpoint_steps", self.interval),
                        ("validation_cases", self.cases),
                    ]:
                        if key in options:
                            widget.setValue(options[key])
                    self.minutes.setValue(2)
                    if options.get("domain"):
                        index = self.domain.findData(options["domain"])
                        if index < 0:
                            raise ValueError("Unknown smoke domain")
                        self.domain.setCurrentIndex(index)
                    self.initial.setCurrentIndex(
                        0 if options.get("fresh", False) else 1
                    )
                    if self.smoke.get("bad_engine"):
                        self.engine.setText(self.smoke["bad_engine"])
                    self.start.click()
                    self.smoke_phase = "training"
            elif self.run_path:
                view = snapshot(self.run_path)
                state = view["state"]
                if view["phase"] == "failed":
                    if self.smoke.get("bad_engine"):
                        atomic_json(
                            self.root / "smoke_done.json",
                            {"expected_failure": True, "run": str(self.run_path)},
                        )
                        self.close()
                        return
                    raise RuntimeError(
                        read_json(self.run_path / "desktop_failure.json").get(
                            "message", "worker_failed"
                        )
                    )
                if self.smoke_phase == "training" and state.get(
                    "trained_rollout_transitions", 0
                ) >= self.smoke.get("stop_after", 1024):
                    self.refresh()
                    self.grab().save(str(self.root / "trainer_smoke.png"))
                    if self.smoke.get("close_without_stop"):
                        atomic_json(
                            self.root / "smoke_detached.json",
                            {
                                "run": str(self.run_path),
                                "transitions": state["transitions"],
                                "pid": view["heartbeat"]["pid"],
                            },
                        )
                        self.close()
                        return
                    self.request_stop()
                    self.smoke_phase = "stopping"
                elif self.smoke_phase == "stopping" and not view["alive"]:
                    atomic_json(
                        self.root / "smoke_stopped.json",
                        {
                            "run": str(self.run_path),
                            "transitions": state["transitions"],
                            "has_latest": bool(state.get("latest")),
                        },
                    )
                    self.close()
                    return
                elif (
                    self.smoke_phase == "resume"
                    and not view["alive"]
                    and view["phase"] == "completed"
                ):
                    assert state["transitions"] > self.smoke_resume_transitions
                    atomic_json(
                        self.root / "smoke_done.json",
                        {
                            "run": str(self.run_path),
                            "transitions": state["transitions"],
                            "resumed": True,
                        },
                    )
                    self.grab().save(str(self.root / "trainer_resumed.png"))
                    self.close()
                    return
                elif (
                    self.smoke_phase == "evaluation"
                    and not view["alive"]
                    and view["phase"] == "completed"
                ):
                    assert (self.run_path / "manual_validation.json").exists()
                    atomic_json(
                        self.root / "smoke_evaluated.json", {"run": str(self.run_path)}
                    )
                    self.grab().save(str(self.root / "trainer_evaluated.png"))
                    self.close()
                    return
        except BaseException as error:
            self.error(error)
            return
        QTimer.singleShot(500, self.smoke_tick)


def main(root=None, smoke_plan=None):
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("PokeAdvice AI Trainer")
    app.setOrganizationName("PokeAdvice")
    window = TrainerWindow(root, smoke_plan)
    window.show()
    return app.exec()
