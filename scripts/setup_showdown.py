"""Build the pinned simulator in a new external directory; never modify a checkout."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from advisor.showdown_bridge import SHOWDOWN_COMMIT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists():
        parser.error("destination must be a new directory; existing work is never overwritten")
    repository = Path(__file__).resolve().parents[1]
    if destination.is_relative_to(repository):
        parser.error("use an external workspace outside the PokeAdvice repository")
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not npm or not shutil.which("node"):
        parser.error("Node >=22.18 and npm are required")
    destination.mkdir(parents=True)
    for command in (
        ["git", "init", "--quiet"],
        ["git", "remote", "add", "origin", "https://github.com/smogon/pokemon-showdown.git"],
        ["git", "fetch", "--depth=1", "origin", SHOWDOWN_COMMIT],
        ["git", "checkout", "--detach", "FETCH_HEAD"],
        [npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
        ["node", "build"],
    ):
        subprocess.run(command, cwd=destination, check=True)
    print(f"Pinned offline simulator ready: {destination}")


if __name__ == "__main__":
    main()
