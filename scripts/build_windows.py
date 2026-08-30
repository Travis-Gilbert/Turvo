#!/usr/bin/env python3
"""Build with Cargo and stage ANGLE from that invocation's native outputs."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ANGLE_LIBRARIES = ("libEGL.dll", "libGLESv2.dll")


def stage_angle(outputs: set[Path], profile_directory: Path) -> None:
    profile_directory = profile_directory.resolve()
    candidates = [
        output for output in {path.resolve() for path in outputs}
        if output.parent.parent == profile_directory / "build"
        and all((output / name).is_file() for name in ANGLE_LIBRARIES)
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one current target ANGLE output, got {len(candidates)}")
    for name in ANGLE_LIBRARIES:
        source = candidates[0] / name
        for destination in (profile_directory, profile_directory / "deps"):
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination / name)
        with source.open("rb") as library:
            digest = hashlib.file_digest(library, "sha256").hexdigest()
        print(f"Staged {name} from current mozangle build; SHA-256 {digest}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_directory", type=Path)
    parser.add_argument("cargo_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    cargo_args = args.cargo_args
    if cargo_args[:1] == ["--"]:
        cargo_args = cargo_args[1:]
    if not cargo_args or cargo_args[0] not in {"build", "test"}:
        parser.error("supply cargo build or cargo test --no-run arguments after --")
    if cargo_args[0] == "test" and "--no-run" not in cargo_args:
        parser.error("test must use --no-run; libraries are staged before execution")
    outputs = set()
    with subprocess.Popen(
        ["cargo", *cargo_args, "--message-format=json"],
        stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
    ) as process:
        for line in process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                print(line, end="", flush=True)
                continue
            if message.get("reason") == "compiler-message":
                print(message["message"].get("rendered", ""), end="", flush=True)
            if message.get("reason") == "build-script-executed":
                package = message.get("package_id", "").rsplit("#", 1)[-1]
                if package.startswith("mozangle@"):
                    outputs.add(Path(message["out_dir"]).resolve())
        result = process.wait()
    if result:
        return result
    try:
        stage_angle(outputs, args.profile_directory)
    except (OSError, RuntimeError) as error:
        print(f"Native library staging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
