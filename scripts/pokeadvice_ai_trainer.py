"""PokeAdvice AI Trainer entry point, including frozen multiprocessing dispatch."""

from pathlib import Path
import sys
import os
import multiprocessing
import subprocess

# Apply only in this separate desktop executable, including spawn interpreters.
# Native Node/Git children otherwise create visible console windows under a GUI.
if os.name == "nt":

    class HiddenChildren(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            kwargs["creationflags"] = (
                kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
            )
            super().__init__(*args, **kwargs)

    subprocess.Popen = HiddenChildren

# Windowed bootloaders expose None streams, including spawn children.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument(
        "--smoke-plan", type=Path, help="Explicit bounded local release-test plan"
    )
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    if args.worker:
        from trainer_app.worker import execute

        raise SystemExit(
            execute(args.worker, resume=args.resume, evaluate=args.evaluate)
        )
    try:
        from trainer_app.gui import main

        result = main(args.data_root, args.smoke_plan)
    except Exception:
        import traceback

        destination = (
            Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PokeAdviceAITrainer"
        )
        destination.mkdir(parents=True, exist_ok=True)
        log = destination / "startup_failure.log"
        log.write_text(traceback.format_exc(), encoding="utf-8")
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None, "앱 시작 실패. 진단: " + str(log), "PokeAdvice AI Trainer", 0x10
            )
        result = 1
    raise SystemExit(result)
