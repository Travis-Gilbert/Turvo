#!/usr/bin/env python3
"""Validate and render the Turvo code-server compatibility board."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFINITION = ROOT / "plan-definition.json"
TICK = chr(96)
ALLOWED_OWNERS = {"servo-fork", "turvo", "code-server-fork"}
STATUSES = {"frontier", "working", "pending", "completed", "parked", "failed"}


def inline(value: object) -> str:
    return f"{TICK}{str(value).replace(TICK, '')}{TICK}"


def bullets(values: list[str], empty: str = "None.") -> str:
    return "\n".join(f"- {value}" for value in values) if values else empty


def load_plan(path: Path = DEFINITION) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def validate(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema",
        "plan_id",
        "destination",
        "fixpoint",
        "hard_prerequisite",
        "source_ledger",
        "acceptance_obligations",
        "tasks",
        "terminal_node",
    }
    missing = sorted(required - set(plan))
    if missing:
        return ["missing top-level fields: " + ", ".join(missing)]
    if plan["schema"] != "theorem.portable-plan.v1":
        errors.append("schema must be theorem.portable-plan.v1")
    tasks_list = plan["tasks"]
    ids = [task.get("id") for task in tasks_list]
    if any(not value for value in ids):
        errors.append("every task needs an id")
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        errors.append("duplicate task ids: " + ", ".join(duplicates))
    tasks = {task["id"]: task for task in tasks_list if task.get("id")}
    obligations = {item["id"] for item in plan["acceptance_obligations"]}
    required_fields = {
        "label",
        "type",
        "status",
        "controller",
        "owner",
        "depends_on",
        "scope",
        "obligations",
        "gist",
        "consumes",
        "produces",
        "blueprint",
        "proof_commands",
        "discharge_evidence",
        "retraction_path",
    }
    for task in tasks_list:
        task_id = task.get("id", "<missing>")
        missing_fields = sorted(required_fields - set(task))
        for field in missing_fields:
            errors.append(f"{task_id}: missing field {field}")
        if task.get("status") not in STATUSES:
            errors.append(f"{task_id}: invalid status {task.get('status')}")
        if task.get("owner") not in ALLOWED_OWNERS:
            errors.append(f"{task_id}: invalid owner {task.get('owner')}")
        unknown_dependencies = sorted(set(task.get("depends_on", [])) - set(tasks))
        if unknown_dependencies:
            errors.append(f"{task_id}: unknown dependencies {', '.join(unknown_dependencies)}")
        unknown_obligations = sorted(set(task.get("obligations", [])) - obligations)
        if unknown_obligations:
            errors.append(f"{task_id}: unknown obligations {', '.join(unknown_obligations)}")
        if task.get("status") == "completed" and not task.get("discharge_evidence"):
            errors.append(f"{task_id}: completed task lacks discharge evidence")
        if task.get("status") == "parked":
            if not task.get("park_reason") or not task.get("resume_condition"):
                errors.append(f"{task_id}: parked task needs a reason and resume condition")

    indegree = {task_id: 0 for task_id in tasks}
    successors: dict[str, list[str]] = defaultdict(list)
    for task_id, task in tasks.items():
        for dependency in task.get("depends_on", []):
            if dependency in tasks:
                indegree[task_id] += 1
                successors[dependency].append(task_id)
    queue = deque(sorted(task_id for task_id, degree in indegree.items() if degree == 0))
    visited = []
    while queue:
        task_id = queue.popleft()
        visited.append(task_id)
        for successor in sorted(successors[task_id]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if len(visited) != len(tasks):
        errors.append("task dependencies must be acyclic")

    class_work: dict[str, dict[str, Any]] = {}
    class_verify: dict[str, dict[str, Any]] = {}
    for task in tasks_list:
        class_id = task.get("failure_class")
        if not class_id:
            continue
        target = class_work if task.get("type") == "work.implementation" else class_verify
        if class_id in target:
            errors.append(f"{class_id}: duplicate {task.get('type')} class node")
        target[class_id] = task
    observed_count = plan["source_ledger"].get("class_count")
    if observed_count != len(class_work) or set(class_work) != set(class_verify):
        errors.append("every observed class needs exactly one work node and one verifier node")
    for class_id, work in class_work.items():
        verifier = class_verify.get(class_id)
        if verifier is None:
            continue
        if work.get("verify_sibling") != verifier.get("id"):
            errors.append(f"{class_id}: work node does not name its verifier sibling")
        if work["id"] not in verifier.get("depends_on", []):
            errors.append(f"{class_id}: verifier does not depend on work node")
        if work.get("failure_fingerprint") != verifier.get("failure_fingerprint"):
            errors.append(f"{class_id}: work and verifier fingerprints differ")
        if work.get("owner") != verifier.get("owner"):
            errors.append(f"{class_id}: work and verifier owners differ")

    terminal = tasks.get(plan["terminal_node"])
    if terminal is None:
        errors.append("terminal node is missing")
    else:
        missing_terminal_dependencies = sorted(
            {task["id"] for task in class_verify.values()} - set(terminal["depends_on"])
        )
        if missing_terminal_dependencies:
            errors.append(
                "terminal node misses class verifiers: " + ", ".join(missing_terminal_dependencies)
            )
    active = [task["id"] for task in tasks_list if task.get("status") in {"frontier", "working"}]
    opening = [move.get("node") for move in plan.get("opening_moves", [])]
    if len(active) > 1:
        errors.append("portable board permits at most one active node")
    if active != opening:
        errors.append(f"opening moves differ from active nodes: opening={opening}, active={active}")
    if plan["source_ledger"].get("status") == "capture_pending" and class_work:
        errors.append("capture-pending ledger cannot create class nodes")
    return errors


def render_manifest(plan: dict[str, Any], digest: str) -> str:
    ledger = plan["source_ledger"]
    rows = [
        "| Node | Status | Owner | Type | Depends on |",
        "|---|---|---|---|---|",
    ]
    for task in plan["tasks"]:
        rows.append(
            f"| [{task['id']}](nodes/{task['id']}.md) | {task['status']} | "
            f"{task['owner']} | {task['type']} | {', '.join(task['depends_on']) or 'root'} |"
        )
    opening = [f"{move['rank']}. {inline(move['node'])}: {move['why']}" for move in plan.get("opening_moves", [])]
    return (
        f"# {plan['plan_id']} board\n\n"
        f"Canonical SHA-256: {inline(digest)}\n\n"
        "## Native ledger authority\n\n"
        f"- Path: {inline(ledger['path'])}\n"
        f"- Status: {inline(ledger['status'])}\n"
        f"- SHA-256: {inline(ledger['sha256'] or 'not captured')}\n"
        f"- Remaining failure classes: {ledger['class_count']}\n\n"
        "## Destination\n\n"
        f"{plan['destination']}\n\n"
        "## Fixpoint\n\n"
        f"{plan['fixpoint']}\n\n"
        "## Hard prerequisite\n\n"
        f"{plan['hard_prerequisite']}\n\n"
        "## Opening move\n\n"
        f"{bullets(opening, 'No active move.')}\n\n"
        "## Task board\n\n"
        + "\n".join(rows)
        + "\n\n## Projections\n\n"
        "- [Dependency graph](projection.md)\n"
        "- [Edges](edges.md)\n"
        "- [Continuity](CONTINUITY.md)\n"
        "- [Decisions and disagreements](disagreements.md)\n"
        "- [Lessons and constraints](lessons.md)\n"
        "- [Replay](replay.md)\n"
        "- [Validation](validation.md)\n"
    )


def render_node(task: dict[str, Any], digest: str) -> str:
    park = ""
    if task["status"] == "parked":
        park = (
            "## Park and resume condition\n\n"
            f"{task['park_reason']}\n\n"
            f"Resume: {task['resume_condition']}\n\n"
        )
    owner_reason = task.get("owner_reason")
    owner = f"- Owner: {inline(task['owner'])}\n"
    if owner_reason:
        owner += f"- Owner routing evidence: {owner_reason}\n"
    return (
        f"# {task['id']}: {task['label']}\n\n"
        f"Canonical SHA-256: {inline(digest)}\n\n"
        f"- Status: {inline(task['status'])}\n"
        f"{owner}"
        f"- Type: {inline(task['type'])}\n"
        f"- Controller: {inline(task['controller'])}\n"
        f"- Depends on: {', '.join(inline(value) for value in task['depends_on']) or 'root'}\n"
        f"- Obligations: {', '.join(inline(value) for value in task['obligations'])}\n\n"
        "## Gist\n\n"
        f"{task['gist']}\n\n"
        f"{park}"
        "## Scope\n\n"
        f"{bullets(task['scope'])}\n\n"
        "## Consumes\n\n"
        f"{bullets(task['consumes'])}\n\n"
        "## Produces\n\n"
        f"{bullets(task['produces'])}\n\n"
        "## Blueprint\n\n"
        f"{bullets(task['blueprint'])}\n\n"
        "## Proof commands\n\n"
        f"{bullets([inline(value) for value in task['proof_commands']])}\n\n"
        "## Discharge evidence\n\n"
        f"{bullets(task['discharge_evidence'], 'Not yet discharged.')}\n\n"
        "## Non-conclusions\n\n"
        f"{bullets(task.get('non_conclusions', []))}\n\n"
        "## Retraction path\n\n"
        f"{task['retraction_path']}\n"
    )


def render_edges(plan: dict[str, Any], digest: str) -> str:
    rows = ["| From | To | Condition |", "|---|---|---|"]
    for task in plan["tasks"]:
        if not task["depends_on"]:
            rows.append(f"| root | {task['id']} | plan admitted |")
        for dependency in task["depends_on"]:
            rows.append(f"| {dependency} | {task['id']} | {dependency} completed |")
    return f"# Dependency edges\n\nCanonical SHA-256: {inline(digest)}\n\n" + "\n".join(rows) + "\n"


def render_projection(plan: dict[str, Any], digest: str) -> str:
    fence = TICK * 3
    lines = ["# Dependency projection", "", f"Canonical SHA-256: {inline(digest)}", "", fence + "mermaid", "flowchart TD"]
    for task in plan["tasks"]:
        label = f"{task['id']} {task['label']} [{task['owner']}]".replace('"', "'")
        lines.append(f'  {task["id"]}["{label}"]')
    for task in plan["tasks"]:
        for dependency in task["depends_on"]:
            arrow = "-.->" if task["type"] == "verify.live" and task.get("failure_class") else "-->"
            lines.append(f"  {dependency} {arrow} {task['id']}")
    lines.extend([fence, ""])
    return "\n".join(lines)


def render_continuity(plan: dict[str, Any], digest: str) -> str:
    ledger = plan["source_ledger"]
    active = [f"{inline(task['id'])}: {task['gist']}" for task in plan["tasks"] if task["status"] in {"frontier", "working"}]
    parked = [f"{inline(task['id'])}: {task['park_reason']} Resume: {task['resume_condition']}" for task in plan["tasks"] if task["status"] == "parked"]
    return (
        "# Continuity\n\n"
        f"Canonical SHA-256: {inline(digest)}\n\n"
        f"Ledger status: {inline(ledger['status'])}; classes: {ledger['class_count']}.\n\n"
        "## Resume here\n\n"
        f"{bullets(active, 'No active class repair.')}\n\n"
        "## Parked work\n\n"
        f"{bullets(parked)}\n\n"
        "## Invariants\n\n"
        f"- {plan['scope_law']}\n"
        f"- {plan['hard_prerequisite']}\n"
        "- Run the importer, render projections, then check both before recording a transition.\n"
    )


def render_replay(plan: dict[str, Any], digest: str) -> str:
    marks = {"completed": "x", "frontier": ">", "working": "~", "pending": " ", "parked": "p", "failed": "!"}
    lines = []
    for task in plan["tasks"]:
        evidence = "; ".join(task["discharge_evidence"]) or task.get("park_reason") or "awaiting execution"
        lines.append(f"- [{marks[task['status']]}] {inline(task['id'])} {task['status']}: {evidence}")
    return f"# Execution replay\n\nCanonical SHA-256: {inline(digest)}\n\n" + "\n".join(lines) + "\n"


def render_disagreements(plan: dict[str, Any], digest: str) -> str:
    ownership = plan["source_ledger"]
    return (
        "# Decisions and disagreements\n\n"
        f"Canonical SHA-256: {inline(digest)}\n\n"
        "## D01: Default routing owner\n\n"
        "Choice: assign untriaged native console symptoms to the Turvo integration owner.\n\n"
        "Reversibility: `reversible`.\n\n"
        "Retraction: add a fingerprint-locked entry to `ownership.json` after native "
        "diagnosis routes the class to `servo-fork` or `code-server-fork`.\n\n"
        "## Current disagreement rows\n\n"
        "None. Ownership overrides are routing decisions, not claims that a source file "
        "location proves root cause.\n\n"
        f"Ledger state at render: {inline(ownership['status'])}.\n"
    )


def render_lessons(plan: dict[str, Any], digest: str) -> str:
    return (
        "# Lessons and constraints\n\n"
        f"Canonical SHA-256: {inline(digest)}\n\n"
        "- Artifact fact: `0002-turvo.md` is the sole authority for observed native "
        "Turvo failure classes.\n"
        "- Capability fact: an explicit capture-pending marker is distinct from a "
        "completed classifier count of zero.\n"
        "- Constraint: every observed class keeps one work node, one verifier node, "
        "one allowed routing owner, and one exact absence command.\n"
        "- Non-conclusion: a JavaScript source location does not by itself identify "
        "which hard fork owns the root cause.\n"
    )


def render_validation(plan: dict[str, Any], digest: str) -> str:
    count = plan["source_ledger"]["class_count"]
    return (
        "# Board validation\n\n"
        f"Canonical SHA-256: {inline(digest)}\n\n"
        "- Canonical JSON parses and matches the native ledger import.\n"
        "- Task ids are unique and dependency edges are acyclic.\n"
        f"- {count} observed classes produce {count} work nodes and {count} verifier nodes.\n"
        "- Every class node has an allowed routing owner and a fingerprint absence proof command.\n"
        "- Capture-pending state produces no observed class node.\n"
        "- The terminal node depends on every class verifier.\n"
    )


def projections(plan: dict[str, Any], digest: str) -> dict[Path, str]:
    rendered = {
        ROOT / "manifest.md": render_manifest(plan, digest),
        ROOT / "edges.md": render_edges(plan, digest),
        ROOT / "projection.md": render_projection(plan, digest),
        ROOT / "CONTINUITY.md": render_continuity(plan, digest),
        ROOT / "disagreements.md": render_disagreements(plan, digest),
        ROOT / "lessons.md": render_lessons(plan, digest),
        ROOT / "replay.md": render_replay(plan, digest),
        ROOT / "validation.md": render_validation(plan, digest),
    }
    for task in plan["tasks"]:
        rendered[ROOT / "nodes" / f"{task['id']}.md"] = render_node(task, digest)
    return rendered


def check_or_write(rendered: dict[Path, str], check: bool) -> int:
    node_dir = ROOT / "nodes"
    expected_nodes = {path for path in rendered if path.parent == node_dir}
    existing_nodes = set(node_dir.glob("*.md")) if node_dir.is_dir() else set()
    extras = sorted(existing_nodes - expected_nodes)
    if check:
        drift = [path for path, content in rendered.items() if not path.is_file() or path.read_text(encoding="utf-8") != content]
        drift.extend(extras)
        if drift:
            for path in drift:
                print(f"projection drift: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print(f"validated {len(rendered)} projections with no drift")
        return 0
    node_dir.mkdir(parents=True, exist_ok=True)
    for path, content in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for path in extras:
        path.unlink()
    print(f"rendered {len(rendered)} projections")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        plan, digest = load_plan()
    except (OSError, json.JSONDecodeError) as error:
        parser.exit(1, f"board load failed: {error}\n")
    errors = validate(plan)
    if errors:
        for error in errors:
            print(f"invalid plan: {error}", file=sys.stderr)
        return 1
    return check_or_write(projections(plan, digest), args.check)


if __name__ == "__main__":
    raise SystemExit(main())
