#!/usr/bin/env python3
"""Import the native Turvo VS Code ledger into a portable plan definition."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[1]
DEFAULT_LEDGER = REPOSITORY / "docs/ledgers/vscode/0002-turvo.md"
TEMPLATE = ROOT / "plan-template.json"
OWNERSHIP = ROOT / "ownership.json"
DEFINITION = ROOT / "plan-definition.json"
ALLOWED_OWNERS = {"servo-fork", "turvo", "code-server-fork"}
CLASS_ID_RE = re.compile(r"VSC-\d{3}")
CLASS_HEADING_RE = re.compile(r"(?m)^### (VSC-\d{3})\s*$")
FINGERPRINT_RE = re.compile(
    r"<!--\s*vscode-ledger-class:\s*(VSC-\d{3})\s+fingerprint:\s*([0-9a-f]{64})\s*-->"
)
DECLARED_COUNT_RE = re.compile(r"Classified failure classes:\s*(?:<code>)?(\d+)(?:</code>)?")
CODE_FIELD_RE = re.compile(r"^- (?P<label>Source|First message line):\s*<code>(?P<value>.*)</code>\s*$", re.MULTILINE)


@dataclass(frozen=True)
class FailureClass:
    class_id: str
    fingerprint: str
    source: str
    message: str


@dataclass(frozen=True)
class LedgerCapture:
    status: str
    digest: str | None
    classes: tuple[FailureClass, ...]
    reason: str


class LedgerError(ValueError):
    """Raised when a ledger cannot be imported without inventing state."""


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LedgerError(f"{path.name} must contain a JSON object")
    return value


def _field(section: str, label: str) -> str:
    values = {
        match.group("label"): html.unescape(match.group("value"))
        for match in CODE_FIELD_RE.finditer(section)
    }
    value = values.get(label)
    if value is None:
        raise LedgerError(f"failure class is missing {label}")
    return value


def parse_ledger(path: Path) -> LedgerCapture:
    if not path.is_file():
        return LedgerCapture(
            status="capture_pending",
            digest=None,
            classes=(),
            reason=f"{path.as_posix()} does not exist",
        )

    raw = path.read_bytes()
    text = raw.decode("utf-8")
    digest = sha256(raw)
    if re.search(r"(?im)^Status:\s*(?:native\s+)?capture pending\.?\s*$", text):
        return LedgerCapture(
            status="capture_pending",
            digest=digest,
            classes=(),
            reason="the ledger explicitly records capture pending",
        )

    count_match = DECLARED_COUNT_RE.search(text)
    if count_match is None:
        raise LedgerError(
            "0002-turvo.md must record 'Classified failure classes: N' before it can drive the board"
        )
    declared_count = int(count_match.group(1))
    headings = list(CLASS_HEADING_RE.finditer(text))
    classes: list[FailureClass] = []
    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()
    for index, heading in enumerate(headings):
        class_id = heading.group(1)
        section_end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section = text[heading.end() : section_end]
        fingerprint_match = FINGERPRINT_RE.search(section)
        if fingerprint_match is None or fingerprint_match.group(1) != class_id:
            raise LedgerError(f"{class_id} is missing its matching stable fingerprint comment")
        fingerprint = fingerprint_match.group(2)
        if class_id in seen_ids:
            raise LedgerError(f"duplicate failure class id: {class_id}")
        if fingerprint in seen_fingerprints:
            raise LedgerError(f"duplicate failure class fingerprint: {fingerprint}")
        seen_ids.add(class_id)
        seen_fingerprints.add(fingerprint)
        classes.append(
            FailureClass(
                class_id=class_id,
                fingerprint=fingerprint,
                source=_field(section, "Source"),
                message=_field(section, "First message line"),
            )
        )
    if declared_count != len(classes):
        raise LedgerError(
            f"ledger declares {declared_count} classes but contains {len(classes)} class sections"
        )
    return LedgerCapture(
        status="captured",
        digest=digest,
        classes=tuple(sorted(classes, key=lambda item: item.class_id)),
        reason="native Turvo console capture classified",
    )


def parse_ownership(
    capture: LedgerCapture, ownership: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    default_owner = ownership.get("default_owner")
    if default_owner not in ALLOWED_OWNERS:
        raise LedgerError("ownership.default_owner is not an allowed owner")
    raw_overrides = ownership.get("overrides", {})
    if not isinstance(raw_overrides, dict):
        raise LedgerError("ownership.overrides must be an object")
    observed = {item.class_id: item for item in capture.classes}
    routes: dict[str, dict[str, Any]] = {}
    for item in capture.classes:
        override = raw_overrides.get(item.class_id)
        if override is None:
            routes[item.class_id] = {
                "owner": default_owner,
                "depends_on": [],
                "reason": ownership.get("default_owner_reason", "default routing owner"),
            }
            continue
        if not isinstance(override, dict):
            raise LedgerError(f"ownership override for {item.class_id} must be an object")
        if override.get("fingerprint") != item.fingerprint:
            raise LedgerError(f"ownership override fingerprint does not match {item.class_id}")
        owner = override.get("owner")
        if owner not in ALLOWED_OWNERS:
            raise LedgerError(f"ownership override for {item.class_id} has an invalid owner")
        dependencies = override.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(
            isinstance(value, str) and CLASS_ID_RE.fullmatch(value)
            for value in dependencies
        ):
            raise LedgerError(f"ownership override for {item.class_id} has invalid dependencies")
        unknown_dependencies = sorted(set(dependencies) - set(observed))
        if unknown_dependencies:
            raise LedgerError(
                f"ownership override for {item.class_id} depends on absent classes: "
                + ", ".join(unknown_dependencies)
            )
        if item.class_id in dependencies:
            raise LedgerError(f"ownership override for {item.class_id} depends on itself")
        routes[item.class_id] = {
            "owner": owner,
            "depends_on": sorted(set(dependencies)),
            "reason": override.get("reason", "fingerprint-locked ownership override"),
        }

    indegree = {class_id: 0 for class_id in routes}
    successors = {class_id: [] for class_id in routes}
    for class_id, route in routes.items():
        for dependency in route["depends_on"]:
            indegree[class_id] += 1
            successors[dependency].append(class_id)
    queue = deque(sorted(class_id for class_id, value in indegree.items() if value == 0))
    visited = []
    while queue:
        class_id = queue.popleft()
        visited.append(class_id)
        for successor in sorted(successors[class_id]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if len(visited) != len(routes):
        raise LedgerError("class dependency overrides must form a directed acyclic graph")
    return routes


def _node_suffix(class_id: str) -> str:
    return class_id.replace("-", "_")


def _scope(owner: str, class_id: str) -> list[str]:
    return {
        "servo-fork": [f"Travis-Gilbert/servo fork repair for {class_id}"],
        "turvo": [f"Travis-Gilbert/Turvo integration repair for {class_id}"],
        "code-server-fork": [f"Travis-Gilbert/code-server fork repair for {class_id}"],
    }[owner]


def _capture_task(capture: LedgerCapture, ledger_path: Path) -> dict[str, Any]:
    relative = _display_path(ledger_path)
    completed = capture.status == "captured"
    task: dict[str, Any] = {
        "id": "CAPTURE",
        "label": "Capture the Turvo code-server console ledger",
        "type": "weather",
        "status": "completed" if completed else "parked",
        "controller": "world",
        "owner": "turvo",
        "depends_on": [],
        "scope": [relative],
        "obligations": ["CAPTURE"],
        "gist": "Make the native Turvo console export authoritative before creating failure work.",
        "consumes": ["running examples/code-server workbench", "Firefox DevTools console export"],
        "produces": [relative],
        "blueprint": [
            "Launch code-server in Turvo, exercise the workbench, and export the console.",
            "Classify the export into stable VSC-NNN source and first-message fingerprints.",
        ],
        "oracle_class": "native Turvo console capture",
        "implementation_mode": "external_observation",
        "evidence_class": "operator-owned native DevTools export",
        "substitution_allowed": False,
        "live_oracle_required": True,
        "proof_commands": [
            "python3 scripts/vscode-ledger-classify.py --output docs/ledgers/vscode/0002-turvo.md docs/ledgers/vscode/0002-turvo-console.json",
            "python3 plans/TURVO-CODE-SERVER-LEDGER/import_ledger.py --check",
        ],
        "discharge_evidence": (
            [f"Native ledger SHA-256 {capture.digest} classified {len(capture.classes)} classes."]
            if completed
            else []
        ),
        "non_conclusions": [
            "A pending file, source audit, ServoShell ledger, or screenshot alone does not identify a Turvo failure class."
        ],
        "retraction_path": "Mark the capture pending and regenerate if the native artifact is invalidated.",
    }
    if not completed:
        task["park_reason"] = capture.reason
        task["resume_condition"] = (
            "0002-turvo.md records a completed classifier capture with an explicit class count."
        )
    return task


def _class_tasks(
    item: FailureClass, route: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    suffix = _node_suffix(item.class_id)
    work_id = f"W_{suffix}"
    verify_id = f"V_{suffix}"
    prerequisite_verifiers = [
        f"V_{_node_suffix(class_id)}" for class_id in route["depends_on"]
    ]
    proof_absent = (
        "python3 plans/TURVO-CODE-SERVER-LEDGER/import_ledger.py "
        f"--assert-absent {item.class_id}"
    )
    work = {
        "id": work_id,
        "label": f"Repair {item.class_id}",
        "type": "work.implementation",
        "status": "pending",
        "controller": "agent",
        "owner": route["owner"],
        "owner_reason": route["reason"],
        "failure_class": item.class_id,
        "failure_fingerprint": item.fingerprint,
        "depends_on": ["CAPTURE", *prerequisite_verifiers],
        "scope": _scope(route["owner"], item.class_id),
        "obligations": [item.class_id],
        "verify_sibling": verify_id,
        "gist": f"Remove {item.class_id} without hiding other native console classes.",
        "consumes": [
            f"source {item.source}",
            f"message {item.message}",
            f"fingerprint {item.fingerprint}",
        ],
        "produces": [f"reviewable repair in {route['owner']}", "fresh native Turvo console capture"],
        "blueprint": [
            "Reproduce the exact source and first-message fingerprint in the native Turvo ledger.",
            "Diagnose the owning layer and update ownership.json if evidence routes the repair to a different hard fork.",
            "Implement the bounded repair and repeat the full workbench capture.",
        ],
        "oracle_class": "stable console fingerprint absent from a fresh native capture",
        "implementation_mode": "hard_fork_repair",
        "evidence_class": "exact native console recapture",
        "substitution_allowed": False,
        "live_oracle_required": True,
        "proof_commands": [proof_absent],
        "discharge_evidence": [],
        "non_conclusions": [
            "Changing the source location or message text is not by itself proof that the behavior works.",
            "The absence oracle applies only to this fingerprint and does not discharge another VSC class.",
        ],
        "retraction_path": "Restore the repair and reopen this node if the exact fingerprint returns in a later native capture.",
    }
    verify = {
        "id": verify_id,
        "label": f"Verify {item.class_id} is absent",
        "type": "verify.live",
        "status": "pending",
        "controller": "verifier",
        "owner": route["owner"],
        "failure_class": item.class_id,
        "failure_fingerprint": item.fingerprint,
        "depends_on": [work_id],
        "scope": [f"read-only native recapture for {item.class_id}"],
        "obligations": [item.class_id],
        "gist": f"Independently prove that native Turvo no longer reports {item.class_id}.",
        "consumes": ["fresh 0002-turvo.md", f"repair receipt from {work_id}"],
        "produces": [f"absence receipt for {item.class_id}"],
        "blueprint": [
            "Run the full native capture independently.",
            "Require the exact fingerprint to be absent while retaining every other observed class.",
        ],
        "oracle_class": "independent native fingerprint absence",
        "implementation_mode": "adversarial_recapture",
        "evidence_class": "operator-owned native DevTools export",
        "substitution_allowed": False,
        "live_oracle_required": True,
        "proof_commands": [proof_absent],
        "discharge_evidence": [],
        "non_conclusions": [
            "Unit tests, compilation, or a source diff cannot substitute for the native absence receipt."
        ],
        "retraction_path": "Reopen the work node if the fingerprint reappears.",
    }
    return work, verify


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPOSITORY).as_posix()
    except ValueError:
        return path.as_posix()


def build_plan(
    template: dict[str, Any],
    capture: LedgerCapture,
    routes: dict[str, dict[str, Any]],
    ledger_path: Path,
) -> dict[str, Any]:
    plan = json.loads(json.dumps(template))
    tasks = [_capture_task(capture, ledger_path)]
    for item in capture.classes:
        tasks.extend(_class_tasks(item, routes[item.class_id]))

    verifier_ids = [f"V_{_node_suffix(item.class_id)}" for item in capture.classes]
    capture_complete = capture.status == "captured"
    fixpoint_complete = capture_complete and not capture.classes
    tasks.append(
        {
            "id": "FIXPOINT",
            "label": "Verify the code-server compatibility fixpoint",
            "type": "verify.live",
            "status": "completed" if fixpoint_complete else "pending",
            "controller": "verifier",
            "owner": "turvo",
            "depends_on": ["CAPTURE", *verifier_ids],
            "scope": ["read-only docs/ledgers/vscode/0002-turvo.md"],
            "obligations": ["FIXPOINT"],
            "gist": "Accept the board only when the completed native capture contains zero remaining classes.",
            "consumes": ["completed CAPTURE", "all class verifier receipts"],
            "produces": ["compatibility ledger fixpoint receipt"],
            "blueprint": [
                "Require an explicit native classifier count of zero.",
                "Reject a missing ledger, capture-pending marker, or lower-class substitute.",
            ],
            "oracle_class": "native Turvo ledger with zero classified failure classes",
            "implementation_mode": "terminal_live_verification",
            "evidence_class": "operator-owned native DevTools export",
            "substitution_allowed": False,
            "live_oracle_required": True,
            "proof_commands": [
                "python3 plans/TURVO-CODE-SERVER-LEDGER/import_ledger.py --assert-empty"
            ],
            "discharge_evidence": (
                [f"Native ledger SHA-256 {capture.digest} declares zero failure classes."]
                if fixpoint_complete
                else []
            ),
            "non_conclusions": [
                "Zero classes in an unclassified or capture-pending document is not a fixpoint receipt."
            ],
            "retraction_path": "Regenerate the board when a later native capture reports a VSC class.",
        }
    )

    if capture_complete and capture.classes:
        ready = [
            task
            for task in tasks
            if task["type"] == "work.implementation"
            and task["depends_on"] == ["CAPTURE"]
        ]
        if ready:
            ready[0]["status"] = "frontier"
            plan["opening_moves"] = [
                {
                    "rank": 1,
                    "node": ready[0]["id"],
                    "why": "It is the lowest stable class id with no unresolved class dependency.",
                }
            ]
        else:
            plan["opening_moves"] = []
    else:
        plan["opening_moves"] = []

    plan["source_ledger"] = {
        "path": _display_path(ledger_path),
        "status": capture.status,
        "sha256": capture.digest,
        "class_count": len(capture.classes),
        "reason": capture.reason,
    }
    plan["acceptance_obligations"] = [
        {
            "id": "CAPTURE",
            "text": "A completed native Turvo console capture is the class authority.",
            "oracle": "0002-turvo.md declares its classifier count and carries stable fingerprint comments.",
        },
        *[
            {
                "id": item.class_id,
                "text": f"The exact native console fingerprint {item.fingerprint} is absent after repair.",
                "oracle": f"import_ledger.py --assert-absent {item.class_id} passes against a fresh native capture.",
            }
            for item in capture.classes
        ],
        {
            "id": "FIXPOINT",
            "text": "The completed native ledger contains zero remaining failure classes.",
            "oracle": "import_ledger.py --assert-empty passes.",
        },
    ]
    plan["tasks"] = tasks
    plan["terminal_node"] = "FIXPOINT"
    return plan


def canonical_bytes(plan: dict[str, Any]) -> bytes:
    return (json.dumps(plan, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def generate(ledger_path: Path) -> tuple[LedgerCapture, dict[str, Any], bytes]:
    capture = parse_ledger(ledger_path)
    template = load_json(TEMPLATE)
    ownership = load_json(OWNERSHIP)
    routes = parse_ownership(capture, ownership)
    plan = build_plan(template, capture, routes, ledger_path)
    return capture, plan, canonical_bytes(plan)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--assert-empty", action="store_true")
    parser.add_argument("--assert-absent", metavar="VSC-NNN")
    args = parser.parse_args()
    try:
        capture, _, rendered = generate(args.ledger)
        if args.assert_absent:
            if not CLASS_ID_RE.fullmatch(args.assert_absent):
                raise LedgerError("--assert-absent requires a VSC-NNN id")
            if capture.status != "captured":
                raise LedgerError("class absence requires a completed native capture")
            if any(item.class_id == args.assert_absent for item in capture.classes):
                raise LedgerError(f"{args.assert_absent} remains present")
            print(f"{args.assert_absent} is absent from the completed native ledger")
            return 0
        if args.assert_empty:
            if capture.status != "captured":
                raise LedgerError("fixpoint requires a completed native capture")
            if capture.classes:
                raise LedgerError(
                    "native ledger still contains: "
                    + ", ".join(item.class_id for item in capture.classes)
                )
            print("completed native ledger contains zero failure classes")
            return 0
        if args.check:
            if not DEFINITION.is_file() or DEFINITION.read_bytes() != rendered:
                raise LedgerError("plan-definition.json does not match the native ledger import")
            print("plan definition matches the native ledger import")
            return 0
        temporary = DEFINITION.with_suffix(".json.tmp")
        temporary.write_bytes(rendered)
        temporary.replace(DEFINITION)
        print(
            f"imported {len(capture.classes)} classes from {capture.status} ledger into {DEFINITION}"
        )
        return 0
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, LedgerError) as error:
        parser.exit(1, f"ledger plan import failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
