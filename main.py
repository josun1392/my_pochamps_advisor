from __future__ import annotations

import sys
import argparse
import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(description="PokeAdvice human battle advisor")
    parser.add_argument("--showdown-shadow", type=Path, help="local JSON containing explicit hypothetical teams, opponent choices and seeds")
    parser.add_argument("--showdown-checkout", type=Path, help="external pinned, built Pokémon Showdown checkout")
    parser.add_argument("--showdown-experimental-ranking", action="store_true", help="display separate experimental sampled ranking; default recommendation policy stays unchanged")
    args, qt_args = parser.parse_known_args()
    context = None
    if args.showdown_shadow is not None:
        if args.showdown_checkout is None: parser.error("--showdown-shadow requires --showdown-checkout")
        try:
            if args.showdown_shadow.stat().st_size > 8 * 1024 * 1024: raise ValueError()
            context = json.loads(args.showdown_shadow.read_text(encoding="utf-8"))
            if not isinstance(context, dict) or context.get("schema_version") not in {"showdown-shadow-config-v1", "showdown-shadow-config-v2"}: raise ValueError()
        except (OSError, ValueError): parser.error("invalid local Showdown shadow configuration")
    elif args.showdown_checkout is not None:
        parser.error("--showdown-checkout requires --showdown-shadow")
    if args.showdown_experimental_ranking and (context is None or context.get("schema_version") != "showdown-shadow-config-v2"):
        parser.error("--showdown-experimental-ranking requires a v2 Showdown shadow configuration")
    app = QApplication([sys.argv[0], *qt_args])
    window = MainWindow()
    if context is not None:
        options = {"checkout": args.showdown_checkout, "context": context}
        if args.showdown_experimental_ranking: options["experimental_ranking"] = True
        window.configure_showdown_shadow(**options)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
