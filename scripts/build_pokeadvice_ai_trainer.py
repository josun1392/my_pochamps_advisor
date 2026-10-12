"""Reproducible Windows onedir bundle, entirely outside the source repository."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from hashlib import sha256
import importlib.metadata
import json
import os
import shutil
import subprocess
from time import perf_counter

from advisor.learning_resources import WindowsJob, atomic_json
from advisor.showdown_bridge import ShowdownBridge, SHOWDOWN_COMMIT

ROOT = Path(__file__).resolve().parents[1]


def build(checkout, output):
    output = Path(output).resolve()
    if output.exists() or output == ROOT or ROOT in output.parents:
        raise ValueError("New distribution path outside repository required")
    ShowdownBridge(checkout)._verify_checkout()
    job = WindowsJob(memory_mib=8192, cpu_percent=50, active_process_limit=24)
    start = perf_counter()
    output.mkdir(parents=True)
    stage = output / "payload"
    stage.mkdir()
    models = [
        "showdown_mc_domain_v1",
        "showdown_full_domain_v7",
        "showdown_full_roster_v8",
        "showdown_native_curriculum_v6",
        "showdown_native_fresh17",
        "showdown_tactics_v1",
    ]
    for directory in models:
        shutil.copytree(ROOT / "models" / directory, stage / "models" / directory)
    shutil.copytree(
        ROOT / "models/showdown_full_mc_study_v1/catalog_bindings",
        stage / "models/showdown_full_mc_study_v1/catalog_bindings",
    )
    source_files = list((ROOT / "trainer_app").glob("*.py")) + [
        p
        for p in (ROOT / "advisor").glob("*.py")
        if p.name.startswith(("learned_", "learning_", "showdown_"))
    ]
    source_files += [
        ROOT / "scripts" / name
        for name in [
            "train_showdown_autonomous.py",
            "evaluate_showdown_policy.py",
            "build_showdown_full_domain.py",
            "build_showdown_full_roster.py",
        ]
    ]
    for source in source_files:
        relative = source.relative_to(ROOT)
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    shutil.copytree(
        ROOT / "tools/showdown_bridge",
        stage / "tools/showdown_bridge",
        ignore=shutil.ignore_patterns("node_modules"),
    )
    native = stage / "runtime/showdown"
    native.parent.mkdir(parents=True)
    subprocess.run(
        [
            "git",
            "clone",
            "--local",
            "--no-hardlinks",
            str(Path(checkout).resolve()),
            str(native),
        ],
        check=True,
        capture_output=True,
    )
    for directory in ("dist", "node_modules"):
        shutil.copytree(Path(checkout) / directory, native / directory)
    ShowdownBridge(native)._verify_checkout()
    binaries = stage / "runtime/bin"
    binaries.mkdir()
    node = Path(shutil.which("node"))
    git = Path("C:/Program Files/Git/mingw64/bin/git.exe")
    if not git.is_file():
        raise ValueError(
            "Verified Git-for-Windows installation required to build portable runtime"
        )
    shutil.copyfile(node, binaries / "node.exe")
    shutil.copyfile(git, binaries / "git.exe")
    import pefile

    pending = [git]
    copied = set()
    while pending:
        binary = pending.pop()
        for entry in pefile.PE(str(binary)).DIRECTORY_ENTRY_IMPORT:
            dll = git.parent / entry.dll.decode()
            if dll.is_file() and dll.name.lower() not in copied:
                copied.add(dll.name.lower())
                shutil.copyfile(dll, binaries / dll.name)
                pending.append(dll)
    licenses = stage / "THIRD_PARTY_LICENSES"
    licenses.mkdir()
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", licenses / "CPython-LICENSE")
    for distribution in importlib.metadata.distributions():
        for entry in distribution.files or []:
            if any(
                part.lower().startswith(("license", "copying", "notice"))
                for part in entry.parts
            ) and ".dist-info" in str(entry):
                source = distribution.locate_file(entry)
                if source.is_file():
                    target = (
                        licenses
                        / distribution.metadata["Name"]
                        / str(entry).split(".dist-info/", 1)[-1]
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    shutil.copyfile(Path(checkout) / "LICENSE", licenses / "pokemon-showdown-LICENSE")
    shutil.copytree(
        "C:/Program Files/Git/usr/share/licenses", licenses / "Git-for-Windows"
    )
    git_license = Path("C:/Program Files/Git/mingw64/share/licenses")
    if git_license.exists():
        shutil.copytree(git_license, licenses / "Git-MinGW")
    # Node Windows installer includes its complete third-party notice.
    node_license = node.parent / "LICENSE"
    if not node_license.exists():
        version = subprocess.check_output([str(node), "--version"], text=True).strip()
        if version != "v22.20.0":
            raise ValueError("Bundled Node license only verified for v22.20.0")
        node_license = ROOT / "packaging/node-v22.20.0-LICENSE.txt"
    if node_license.exists():
        shutil.copyfile(node_license, licenses / "Node-LICENSE")
    else:
        raise ValueError("Node LICENSE missing; do not ship without notice")
    (licenses / "README.txt").write_text(
        "Qt/PySide6 DLLs remain separate and replaceable (LGPLv3); no GPL-only Qt modules are used. Source/license links: https://doc.qt.io/qtforpython-6/ https://github.com/qtproject/pyside-pyside-setup https://github.com/git/git https://github.com/git-for-windows/git https://github.com/nodejs/node https://github.com/pytorch/pytorch https://github.com/smogon/pokemon-showdown https://github.com/Stable-Baselines-Team/stable-baselines3 https://github.com/Stable-Baselines-Team/stable-baselines3-contrib\nThis local distribution uses unmodified upstream DLLs/runtimes. PyInstaller bootloader exception permits application packaging. Engine source and Git objects are included; no downloads occur while training.\n",
        encoding="utf-8",
    )
    files = {
        str(p.relative_to(stage)).replace("\\", "/"): sha256(p.read_bytes()).hexdigest()
        for p in stage.rglob("*")
        if p.is_file() and "THIRD_PARTY_LICENSES" not in p.parts
    }
    atomic_json(
        stage / "trainer_payload.json",
        {
            "schema_version": "pokeadvice-trainer-payload-v1",
            "engine_commit": SHOWDOWN_COMMIT,
            "files": files,
            "licenses": "THIRD_PARTY_LICENSES",
            "cpu_only": True,
        },
    )
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        "--windowed",
        "--name",
        "PokeAdvice AI Trainer",
        "--distpath",
        str(output / "distribution"),
        "--workpath",
        str(output / "build"),
        "--specpath",
        str(output),
        "--add-data",
        str(stage) + ";.",
        "--collect-all",
        "poke_env",
        "--collect-data",
        "stable_baselines3",
        "--collect-data",
        "sb3_contrib",
        "--copy-metadata",
        "torch",
        "--copy-metadata",
        "sb3-contrib",
        "--copy-metadata",
        "stable-baselines3",
        "--copy-metadata",
        "gymnasium",
        "--copy-metadata",
        "numpy",
        "--exclude-module",
        "PyQt5",
        "--exclude-module",
        "PyQt6",
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "PySide6.QtWebEngineCore",
        str(ROOT / "scripts/pokeadvice_ai_trainer.py"),
    ]
    # Ambient Codex/Anaconda/Poppler PATH can provide an incompatible ICU DLL.
    # Qt uses Windows' system ICU: restrict analysis to the verified toolchains.
    env = os.environ.copy()
    env.update(
        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0"
    )
    env["PATH"] = os.pathsep.join(
        str(p)
        for p in (
            Path(sys.executable).parent,
            Path(sys.base_prefix),
            node.parent,
            git.parent,
            Path(os.environ["SystemRoot"]) / "System32",
            Path(os.environ["SystemRoot"]),
        )
    )
    with (output / "build.log").open("w", encoding="utf-8") as log:
        subprocess.run(
            command, check=True, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT
        )
    directory = output / "distribution/PokeAdvice AI Trainer"
    exe = directory / "PokeAdvice AI Trainer.exe"
    # PyInstaller drops empty directories. Git recognizes detached repositories
    # only when refs/ exists, even if all references are in packed-refs.
    native_pack = directory / "_internal/runtime/showdown"
    (native_pack / ".git/refs").mkdir(parents=True, exist_ok=True)
    portable_git = directory / "_internal/runtime/bin/git.exe"
    for arguments, expected in (
        (["rev-parse", "HEAD"], SHOWDOWN_COMMIT),
        (["status", "--porcelain", "--untracked-files=no"], ""),
    ):
        result = subprocess.check_output(
            [str(portable_git), "-C", str(native_pack), *arguments], text=True, env=env
        ).strip()
        if result != expected:
            raise ValueError("Packaged native Git identity check failed")
    if (directory / "_internal/icuuc.dll").exists():
        raise ValueError("Unexpected non-system ICU DLL; verify Qt ABI before shipping")
    atomic_json(
        output / "build_result.json",
        {
            "exe": str(exe),
            "exe_sha256": sha256(exe.read_bytes()).hexdigest(),
            "distribution_bytes": sum(
                p.stat().st_size for p in directory.rglob("*") if p.is_file()
            ),
            "wall_seconds": perf_counter() - start,
            "resources": job.usage(),
            "pyinstaller": importlib.metadata.version("pyinstaller"),
            "engine_commit": SHOWDOWN_COMMIT,
        },
    )
    print(json.dumps(read_result(output / "build_result.json")))


def read_result(path):
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.checkout, args.output)
