#!/usr/bin/env python3
"""Run the real Servo security fixture and require its structured receipt."""

import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    executable = args.executable.resolve()
    if sys.platform == "win32" and not executable.suffix:
        executable = executable.with_suffix(".exe")
    if not executable.is_file():
        parser.error(f"native fixture does not exist: {executable}")
    command = [str(executable)]
    environment = os.environ.copy()
    environment["RUST_BACKTRACE"] = "1"
    if sys.platform.startswith("linux"):
        command = ["dbus-run-session", "--", "xvfb-run", "-a", *command]
        environment["LIBGL_ALWAYS_SOFTWARE"] = "1"
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        start_new_session=os.name != "nt",
    )
    timed_out = False
    try:
        output, _ = process.communicate(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        # Only terminate the process group created for this invocation.
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
    # Tauri's dependency diagnostic can include an invoke key on malformed
    # requests. Do not forward that diagnostic into logs or uploaded artifacts.
    output = re.sub(r"__TAURI_INVOKE_KEY__ expected[^\r\n]*", "[invoke-key diagnostic redacted]", output)
    print(output, end="" if output.endswith("\n") else "\n")
    reports = Path(".reports")
    reports.mkdir(exist_ok=True)
    (reports / f"native-security-{sys.platform}.log").write_text(output, encoding="utf-8")
    receipts = []
    for line in output.splitlines():
        if line.startswith("TURVO_NATIVE_SECURITY "):
            receipts.append(json.loads(line.removeprefix("TURVO_NATIVE_SECURITY ")))
    passed = (
        not timed_out
        and process.returncode == 0
        and len(receipts) == 1
        and receipts[0].get("passed") is True
    )
    if not passed:
        print(f"Native probe failed: exit={process.returncode}, timeout={timed_out}, receipts={len(receipts)}")
        return 1
    print("Native IPC security receipt verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
