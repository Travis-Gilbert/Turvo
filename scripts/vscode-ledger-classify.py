#!/usr/bin/env python3
"""Classify exported Firefox console errors into stable VS Code ledger classes."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shlex
import sys
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


ERROR_LEVELS = {"assert", "critical", "error", "exception", "fatal", "warn", "warning"}
CONTAINER_KEYS = ("entries", "logs", "messages", "records")
SOURCE_KEYS = ("filename", "fileName", "sourceName", "url", "source")
MESSAGE_KEYS = ("messageText", "text", "description")
FINGERPRINT_RE = re.compile(
    r"<!-- vscode-ledger-class: (VSC-\d{3}) fingerprint: ([0-9a-f]{64}) -->"
)
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
BEARER_RE = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)([?&;\s](?:access[_-]?)?(?:token|secret|password|authorization|api[_-]?key)=)[^&;\s]+"
)


def load_console(path: Path) -> list[dict[str, Any]]:
    """Load a JSON array/object or newline-delimited JSON console export."""

    raw = path.read_text(encoding="utf-8-sig")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as document_error:
        values = []
        for line_number, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError as line_error:
                raise ValueError(
                    f"console export is neither JSON nor JSON Lines; line {line_number}: {line_error.msg}"
                ) from document_error
        value = values
    return list(iter_entries(value))


def iter_entries(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from iter_entries(item)
        return
    if not isinstance(value, dict):
        return
    for key in CONTAINER_KEYS:
        nested = value.get(key)
        if isinstance(nested, list):
            yield from iter_entries(nested)
            return
    yield value


def payload(entry: dict[str, Any]) -> dict[str, Any]:
    nested = entry.get("message")
    if not isinstance(nested, dict):
        return entry
    return {**entry, **nested}


def first_present(entry: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = entry.get(key)
        if value not in (None, ""):
            return value
    return None


def extract_level(entry: dict[str, Any]) -> str:
    item = payload(entry)
    value = first_present(item, ("level", "severity", "logLevel"))
    if value is None and isinstance(item.get("type"), str):
        value = item["type"]
    return str(value or "unknown").strip().lower()


def normalize_source(entry: dict[str, Any]) -> str:
    item = payload(entry)
    source = first_present(item, SOURCE_KEYS)
    if isinstance(source, dict):
        source = first_present(source, ("url", "name", "source"))
    if source is None:
        location = item.get("location")
        if isinstance(location, dict):
            source = first_present(location, SOURCE_KEYS)
    if source is None:
        stack = item.get("stacktrace") or item.get("stackTrace") or item.get("stack")
        if isinstance(stack, list) and stack and isinstance(stack[0], dict):
            source = first_present(stack[0], SOURCE_KEYS)
    text = str(source or "<unknown>").strip()
    parts = urlsplit(text)
    if parts.scheme and (parts.netloc or parts.scheme == "file"):
        text = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    return text or "<unknown>"


def stringify_message(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(stringify_message(item) for item in value)
    if value is None:
        return ""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def redact(text: str) -> str:
    text = BEARER_RE.sub("Bearer [REDACTED]", text)
    return SECRET_ASSIGNMENT_RE.sub(r"\1[REDACTED]", text)


def first_message_line(entry: dict[str, Any]) -> str:
    item = payload(entry)
    value = first_present(item, MESSAGE_KEYS)
    if value is None and not isinstance(item.get("message"), dict):
        value = item.get("message")
    if value is None:
        value = first_present(item, ("arguments", "parameters", "args"))
    text = ANSI_RE.sub("", stringify_message(value)).replace("\r\n", "\n").replace("\r", "\n")
    first_line = next((line.strip() for line in text.split("\n") if line.strip()), "<empty>")
    return redact(first_line)


def extract_location(entry: dict[str, Any], source: str) -> str:
    item = payload(entry)
    line = first_present(item, ("line", "lineNumber", "lineNo"))
    column = first_present(item, ("column", "columnNumber", "columnNo"))
    if line is None:
        location = item.get("location")
        if isinstance(location, dict):
            line = first_present(location, ("line", "lineNumber", "lineNo"))
            column = first_present(location, ("column", "columnNumber", "columnNo"))
    suffix = ""
    if line is not None:
        suffix += f":{line}"
        if column is not None:
            suffix += f":{column}"
    return source + suffix


def fingerprint(source: str, message: str) -> str:
    return hashlib.sha256(f"{source}\0{message}".encode("utf-8")).hexdigest()


def classify(entries: Iterable[dict[str, Any]], include_all_levels: bool = False) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        level = extract_level(entry)
        if not include_all_levels and level != "unknown" and level not in ERROR_LEVELS:
            continue
        source = normalize_source(entry)
        message = first_message_line(entry)
        key = (source, message)
        group = groups.setdefault(
            key,
            {
                "source": source,
                "message": message,
                "fingerprint": fingerprint(source, message),
                "levels": set(),
                "locations": set(),
                "occurrences": 0,
            },
        )
        group["levels"].add(level)
        group["locations"].add(extract_location(entry, source))
        group["occurrences"] += 1
    return [groups[key] for key in sorted(groups)]


def previous_ids(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    known = {fingerprint: class_id for class_id, fingerprint in FINGERPRINT_RE.findall(path.read_text())}
    if len(set(known.values())) != len(known):
        raise ValueError("existing ledger assigns one VSC id to multiple fingerprints")
    return known


def assign_ids(classes: list[dict[str, Any]], known: dict[str, str]) -> None:
    used = {int(value.removeprefix("VSC-")) for value in known.values()}
    next_id = max(used, default=0) + 1
    for item in classes:
        class_id = known.get(item["fingerprint"])
        if class_id is None:
            if next_id > 999:
                raise ValueError("VSC-NNN identifier space exhausted")
            class_id = f"VSC-{next_id:03d}"
            next_id += 1
        item["id"] = class_id


def load_metadata(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("run metadata must be a JSON object")
    return value


def reproduction_command(metadata: dict[str, Any]) -> str:
    explicit = metadata.get("reproduction_command")
    if isinstance(explicit, list) and all(isinstance(item, str) for item in explicit):
        return shlex.join(explicit)
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    checkout = str(metadata.get("servo_checkout", "/path/to/Travis-Gilbert-servo"))
    workspace = str(metadata.get("workspace", "/path/to/workspace"))
    command = [
        "./scripts/vscode-ledger.sh",
        "--servo-checkout",
        checkout,
        "--bind-addr",
        str(metadata.get("code_server_addr", "127.0.0.1:8080")),
        "--devtools-port",
        str(metadata.get("devtools_port", 6080)),
        "--webdriver-port",
        str(metadata.get("webdriver_port", 7000)),
        workspace,
    ]
    return shlex.join(command)


def code(text: Any) -> str:
    return f"<code>{html.escape(str(text), quote=False)}</code>"


def render(classes: list[dict[str, Any]], metadata: dict[str, Any], console_path: str) -> str:
    command = reproduction_command(metadata)
    profile = metadata.get("profile", "servoshell")
    is_turvo = profile == "turvo"
    revision = metadata.get("servo_revision", "not recorded")
    devtools_port = metadata.get("devtools_port", 6080)
    build_mode = metadata.get("build_mode", "not recorded; capture pending")
    lines = [
        f"# {'Turvo' if is_turvo else 'ServoShell'} VS Code compatibility ledger",
        "",
        "This ledger groups relevant Firefox console entries by normalized source file and",
        "the first non-empty message line. Informational entries are excluded unless the",
        "classifier is run with `--all-levels`.",
        "",
        "## Capture",
        "",
        f"- Servo revision: {code(revision)}",
        f"- Servo build mode: {code(build_mode)}",
        f"- Console export: {code(console_path)}",
        f"- Classified failure classes: {len(classes)}",
        (
            "- Native exercise: workbench render, buffer edit, terminal echo, markdown preview, and extension webview"
            if is_turvo
            else "- Screenshots: `0001-servoshell-load.png` and `0001-servoshell-idle.png`"
        ),
        f"- Firefox attachment: add `localhost:{devtools_port}` in `about:debugging`,",
        "  connect, and inspect the code-server tab.",
        "",
        "## Reproduction",
        "",
        "```sh",
        command,
        "```",
        "",
        "After the native exercise is complete, export the Firefox console and press Enter in the",
        "launcher. To reclassify an existing export without relaunching:",
        "",
        "```sh",
        f"python3 scripts/vscode-ledger-classify.py {console_path}",
        "```",
        "",
        "## Failure classes",
        "",
    ]
    if not classes:
        lines.extend(["No relevant console failure classes were present in this export.", ""])
        return "\n".join(lines)
    for item in sorted(classes, key=lambda value: int(value["id"].removeprefix("VSC-"))):
        levels = ", ".join(sorted(item["levels"]))
        locations = ", ".join(sorted(item["locations"]))
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"<!-- vscode-ledger-class: {item['id']} fingerprint: {item['fingerprint']} -->",
                f"- Source: {code(item['source'])}",
                f"- First message line: {code(item['message'])}",
                f"- Levels: {code(levels)}",
                f"- Occurrences: {item['occurrences']}",
                f"- Observed locations: {code(locations)}",
                "- Reproduce: run the capture command above, attach Firefox DevTools, and",
                "  exercise the workbench until this source/message pair appears.",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "console",
        nargs="?",
        type=Path,
        default=root / "docs/ledgers/vscode/0001-servoshell-console.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "docs/ledgers/vscode/0001-servoshell.md",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=root / ".reports/vscode/0001-servoshell-run.json",
    )
    parser.add_argument("--all-levels", action="store_true")
    args = parser.parse_args()
    try:
        entries = load_console(args.console)
        classes = classify(entries, args.all_levels)
        assign_ids(classes, previous_ids(args.output))
        metadata = load_metadata(args.metadata)
        try:
            console_path = args.console.resolve().relative_to(root).as_posix()
        except ValueError:
            console_path = args.console.as_posix()
        rendered = render(classes, metadata, console_path)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.exit(1, f"VS Code ledger classification failed: {error}\n")
    print(f"Wrote {len(classes)} stable console classes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
