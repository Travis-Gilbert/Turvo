#!/usr/bin/env python3
"""Validate the canonical Turvo completion plan and render its projections."""

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
ACTIVE_STATUSES = {"frontier", "working"}
KNOWN_STATUSES = ACTIVE_STATUSES | {"pending", "completed", "parked", "failed"}
WORK_TYPES = {"work.implementation", "work.external", "work.release"}
VERIFY_TYPES = {"verify.local", "verify.live"}


def inline_code(value: object) -> str:
    return f"{TICK}{str(value).replace(TICK, '')}{TICK}"


def bullets(values: list[str], empty: str = "None.") -> str:
    return "\n".join(f"- {value}" for value in values) if values else empty


def load_plan() -> tuple[dict[str, Any], str]:
    raw = DEFINITION.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def ancestors(task_id: str, tasks: dict[str, dict[str, Any]]) -> set[str]:
    found: set[str] = set()
    queue = list(tasks[task_id]["depends_on"])
    while queue:
        current = queue.pop()
        if current in found:
            continue
        found.add(current)
        queue.extend(tasks[current]["depends_on"])
    return found


def validate(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema",
        "plan_id",
        "generation",
        "destination",
        "fixpoint",
        "hard_prerequisite",
        "acceptance_obligations",
        "palette",
        "gate",
        "autonomy_box",
        "opening_moves",
        "tasks",
        "terminal_node",
    }
    missing = sorted(required - plan.keys())
    if missing:
        return [f"missing top-level fields: {', '.join(missing)}"]
    if plan["schema"] != "theorem.portable-plan.v1":
        errors.append("schema must be theorem.portable-plan.v1")
    if plan["autonomy_box"].get("status") != "granted":
        errors.append("autonomy_box.status must be granted before execution")
    if not str(plan["gate"]).startswith("granted"):
        errors.append("gate must record an explicit grant")
    profile = plan.get("execution_profile")
    if profile:
        required_platforms = set(profile.get("required_platforms", []))
        deferred_platforms = set(profile.get("deferred_platforms", []))
        if not required_platforms:
            errors.append("execution profile needs required platforms")
        if required_platforms & deferred_platforms:
            errors.append("a platform cannot be both required and deferred")
        if deferred_platforms and not profile.get("deferral_reason"):
            errors.append("deferred platforms need an explicit reason")
        if not profile.get("release_gate"):
            errors.append("execution profile needs a release gate")

    task_list = plan["tasks"]
    task_ids = [task.get("id") for task in task_list]
    duplicates = sorted(
        {task_id for task_id in task_ids if task_ids.count(task_id) > 1}
    )
    if duplicates:
        errors.append(f"duplicate task ids: {', '.join(duplicates)}")
    if any(not task_id for task_id in task_ids):
        errors.append("every task needs a non-empty id")
    tasks = {task["id"]: task for task in task_list if task.get("id")}

    obligation_ids = [item.get("id") for item in plan["acceptance_obligations"]]
    if len(obligation_ids) != len(set(obligation_ids)):
        errors.append("acceptance obligation ids must be unique")
    obligations = set(obligation_ids)

    required_task_fields = (
        "label",
        "type",
        "status",
        "controller",
        "depends_on",
        "scope",
        "obligations",
        "gist",
        "consumes",
        "produces",
        "blueprint",
        "oracle_class",
        "implementation_mode",
        "evidence_class",
        "substitution_allowed",
        "live_oracle_required",
        "proof_commands",
        "discharge_evidence",
        "retraction_path",
    )
    for task in task_list:
        task_id = task.get("id", "<missing>")
        for field in required_task_fields:
            if field not in task:
                errors.append(f"{task_id}: missing field {field}")
        task_type = task.get("type")
        if task_type not in plan["palette"]:
            errors.append(f"{task_id}: unknown task type {task_type}")
        elif task.get("controller") != plan["palette"][task_type].get("controller"):
            errors.append(f"{task_id}: controller does not match palette")
        if task.get("status") not in KNOWN_STATUSES:
            errors.append(f"{task_id}: unknown status {task.get('status')}")
        unknown_dependencies = sorted(set(task.get("depends_on", [])) - set(tasks))
        if unknown_dependencies:
            errors.append(
                f"{task_id}: unknown dependencies {', '.join(unknown_dependencies)}"
            )
        unknown_obligations = sorted(set(task.get("obligations", [])) - obligations)
        if unknown_obligations:
            errors.append(
                f"{task_id}: unknown obligations {', '.join(unknown_obligations)}"
            )
        if task.get("live_oracle_required") and task.get("substitution_allowed"):
            errors.append(f"{task_id}: live oracle cannot allow substitution")
        if task.get("status") == "completed" and not task.get("discharge_evidence"):
            errors.append(f"{task_id}: completed task has no discharge evidence")
        if task.get("status") == "parked":
            for field in ("park_reason", "resume_condition"):
                value = task.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{task_id}: parked task needs {field}")

    indegree = {task_id: 0 for task_id in tasks}
    successors: dict[str, list[str]] = defaultdict(list)
    for task_id, task in tasks.items():
        for dependency in task.get("depends_on", []):
            if dependency in tasks:
                indegree[task_id] += 1
                successors[dependency].append(task_id)
    queue = deque(sorted(task_id for task_id, degree in indegree.items() if degree == 0))
    visited: list[str] = []
    while queue:
        task_id = queue.popleft()
        visited.append(task_id)
        for successor in sorted(successors[task_id]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if len(visited) != len(tasks):
        errors.append("task dependencies must form a directed acyclic graph")

    active = [task for task in task_list if task.get("status") in ACTIVE_STATUSES]
    if len(active) > 1:
        errors.append("portable execution permits at most one frontier or working task")
    for task in active:
        incomplete = [
            dependency
            for dependency in task["depends_on"]
            if tasks[dependency].get("status") != "completed"
        ]
        if incomplete:
            errors.append(
                f"{task['id']}: active task has incomplete dependencies "
                + ", ".join(incomplete)
            )
    opening_ids = [move.get("node") for move in plan["opening_moves"]]
    active_ids = [task["id"] for task in active]
    if opening_ids != active_ids:
        errors.append(
            "opening_moves must list the sole active task in execution order "
            f"(opening={opening_ids}, active={active_ids})"
        )

    terminal = plan["terminal_node"]
    if terminal not in tasks:
        errors.append(f"terminal node {terminal} is not defined")
    elif len(visited) == len(tasks):
        terminal_ancestors = ancestors(terminal, tasks) | {terminal}
        unreachable = sorted(set(tasks) - terminal_ancestors)
        if unreachable:
            errors.append(
                f"tasks do not feed the terminal node: {', '.join(unreachable)}"
            )

    for task in task_list:
        if task.get("type") not in WORK_TYPES:
            continue
        sibling_id = task.get("verify_sibling")
        sibling = tasks.get(sibling_id)
        if not sibling:
            errors.append(f"{task['id']}: missing verifier sibling {sibling_id}")
            continue
        if sibling.get("type") not in VERIFY_TYPES:
            errors.append(
                f"{task['id']}: verifier sibling {sibling_id} is not a verifier"
            )
        if task["id"] not in sibling.get("depends_on", []):
            errors.append(
                f"{task['id']}: verifier sibling must depend on the work task"
            )
        if sibling.get("controller") != "verifier":
            errors.append(
                f"{task['id']}: verifier sibling must use verifier controller"
            )

    for obligation in obligations:
        work_coverage = [
            task["id"]
            for task in task_list
            if obligation in task.get("obligations", [])
            and task.get("type") in WORK_TYPES
        ]
        verify_coverage = [
            task["id"]
            for task in task_list
            if obligation in task.get("obligations", [])
            and task.get("type") in VERIFY_TYPES
        ]
        if not work_coverage:
            errors.append(f"{obligation}: no work task coverage")
        if not verify_coverage:
            errors.append(f"{obligation}: no verifier coverage")

    if plan.get("enforce_scope_overlap") and len(visited) == len(tasks):
        work_tasks = [
            task for task in task_list if task.get("type") in WORK_TYPES
        ]
        for index, left in enumerate(work_tasks):
            for right in work_tasks[index + 1 :]:
                ordered = (
                    left["id"] in ancestors(right["id"], tasks)
                    or right["id"] in ancestors(left["id"], tasks)
                )
                if ordered:
                    continue
                overlap = sorted(
                    set(left.get("scope", [])) & set(right.get("scope", []))
                )
                if overlap:
                    errors.append(
                        f"{left['id']} and {right['id']} have parallel "
                        "exact-scope overlap: "
                        + ", ".join(overlap)
                    )
    return errors


def task_mark(task: dict[str, Any]) -> str:
    return {
        "completed": "x",
        "frontier": ">",
        "working": "~",
        "pending": " ",
        "parked": "p",
        "failed": "!",
    }[task["status"]]


def render_manifest(plan: dict[str, Any], digest: str) -> str:
    profile_section = ""
    if profile := plan.get("execution_profile"):
        profile_section = (
            "## Active integration profile\n\n"
            f"Branch: {inline_code(profile['branch'])}\n\n"
            f"Required: {', '.join(profile['required_platforms'])}. "
            f"Deferred: {', '.join(profile['deferred_platforms']) or 'None'}.\n\n"
            f"{profile['deferral_reason']}\n\n"
            f"{profile['dependency_policy']}\n\n"
            f"Release: {profile['release_gate']}\n\n"
        )
    rows = [
        "| Node | Status | Controller | Type | Depends on | Obligations |",
        "|---|---|---|---|---|---|",
    ]
    for task in plan["tasks"]:
        rows.append(
            "| {node} | {status} | {controller} | {kind} | "
            "{dependencies} | {obligations} |".format(
                node=f"[{task['id']}](nodes/{task['id']}.md)",
                status=task["status"],
                controller=task["controller"],
                kind=task["type"],
                dependencies=", ".join(task["depends_on"]) or "root",
                obligations=", ".join(task["obligations"]) or "none",
            )
        )
    opening = [
        f"{move['rank']}. {inline_code(move['node'])}: {move['why']}"
        for move in plan["opening_moves"]
    ]
    return (
        f"# {plan['plan_id']} completion board\n\n"
        f"Canonical SHA-256: {inline_code(digest)}\n\n"
        "## Destination\n\n"
        f"{plan['destination']}\n\n"
        f"{profile_section}"
        "## Fixpoint\n\n"
        f"{plan['fixpoint']}\n\n"
        "## Hard prerequisite\n\n"
        f"{plan['hard_prerequisite']}\n\n"
        "## Authority\n\n"
        f"Gate: {inline_code(plan['gate'])}\n\n"
        f"{plan['gate_note']}\n\n"
        "## Opening move\n\n"
        f"{bullets(opening, 'No active move.')}\n\n"
        "## Task board\n\n"
        + "\n".join(rows)
        + "\n\n"
        "## Projections\n\n"
        "- [Dependency graph](projection.md)\n"
        "- [Edges](edges.md)\n"
        "- [Continuity](CONTINUITY.md)\n"
        "- [Decisions and disagreements](disagreements.md)\n"
        "- [Lessons](lessons.md)\n"
        "- [Replay](replay.md)\n"
        "- [Validation](validation.md)\n"
    )


def render_node(plan: dict[str, Any], task: dict[str, Any], digest: str) -> str:
    commands = [inline_code(command) for command in task["proof_commands"]]
    park_section = ""
    if task["status"] == "parked":
        park_section = (
            "## Park and resume condition\n\n"
            f"{task['park_reason']}\n\n"
            f"Resume: {task['resume_condition']}\n\n"
        )
    progress_section = ""
    if task.get("progress_evidence"):
        progress_section = (
            "## Partial receipts (not discharge)\n\n"
            f"{bullets(task['progress_evidence'])}\n\n"
        )
    fields = [
        f"- Status: {inline_code(task['status'])}",
        f"- Controller: {inline_code(task['controller'])}",
        f"- Type: {inline_code(task['type'])}",
        f"- Depends on: {', '.join(inline_code(item) for item in task['depends_on']) or 'root'}",
        f"- Obligations: {', '.join(inline_code(item) for item in task['obligations']) or 'none'}",
        f"- Oracle class: {task['oracle_class']}",
        f"- Evidence class: {task['evidence_class']}",
        f"- Implementation mode: {inline_code(task['implementation_mode'])}",
        f"- Live oracle required: {inline_code(str(task['live_oracle_required']).lower())}",
        f"- Substitution allowed: {inline_code(str(task['substitution_allowed']).lower())}",
    ]
    return (
        f"# {task['id']}: {task['label']}\n\n"
        f"Canonical SHA-256: {inline_code(digest)}\n\n"
        + "\n".join(fields)
        + "\n\n"
        "## Gist\n\n"
        f"{task['gist']}\n\n"
        f"{park_section}"
        "## Scope\n\n"
        f"{bullets(task['scope'])}\n\n"
        "## Consumes\n\n"
        f"{bullets(task['consumes'])}\n\n"
        "## Produces\n\n"
        f"{bullets(task['produces'])}\n\n"
        "## Blueprint\n\n"
        f"{bullets(task['blueprint'])}\n\n"
        "## Proof commands\n\n"
        f"{bullets(commands, 'No command-based proof; use the declared oracle.')}\n\n"
        "## Discharge evidence\n\n"
        f"{bullets(task['discharge_evidence'], 'Not yet discharged.')}\n\n"
        f"{progress_section}"
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
    return (
        "# Dependency edges\n\n"
        f"Canonical SHA-256: {inline_code(digest)}\n\n"
        + "\n".join(rows)
        + "\n"
    )


def render_projection(plan: dict[str, Any], digest: str) -> str:
    class_names = {
        "completed": "done",
        "frontier": "frontier",
        "working": "working",
        "pending": "pending",
        "parked": "parked",
        "failed": "failed",
    }
    fence = TICK * 3
    lines = [
        "# Dependency projection",
        "",
        f"Canonical SHA-256: {inline_code(digest)}",
        "",
        fence + "mermaid",
        "flowchart TD",
    ]
    for task in plan["tasks"]:
        label = f"{task['id']} {task['label']}".replace('"', "'")
        lines.append(f'  {task["id"]}["{label}"]')
    for task in plan["tasks"]:
        for dependency in task["depends_on"]:
            lines.append(f"  {dependency} --> {task['id']}")
    lines.extend(
        [
            "  classDef done fill:#d8f3dc,stroke:#2d6a4f,color:#081c15",
            "  classDef frontier fill:#ffe8a1,stroke:#9c6b00,color:#332200",
            "  classDef working fill:#bee3f8,stroke:#2b6cb0,color:#102a43",
            "  classDef pending fill:#edf2f7,stroke:#718096,color:#1a202c",
            "  classDef parked fill:#e9d8fd,stroke:#6b46c1,color:#322659",
            "  classDef failed fill:#fed7d7,stroke:#c53030,color:#3b0d0d",
        ]
    )
    by_class: dict[str, list[str]] = defaultdict(list)
    for task in plan["tasks"]:
        by_class[class_names[task["status"]]].append(task["id"])
    for class_name, task_ids in by_class.items():
        if task_ids:
            lines.append(f"  class {','.join(task_ids)} {class_name}")
    lines.extend([fence, ""])
    return "\n".join(lines)


def render_continuity(plan: dict[str, Any], digest: str) -> str:
    active = [task for task in plan["tasks"] if task["status"] in ACTIVE_STATUSES]
    completed = [task for task in plan["tasks"] if task["status"] == "completed"]
    parked = [task for task in plan["tasks"] if task["status"] == "parked"]
    next_lines = [
        f"{inline_code(task['id'])} ({task['status']}): {task['gist']}"
        for task in active
    ]
    completed_lines = [
        f"{inline_code(task['id'])}: {'; '.join(task['discharge_evidence'])}"
        for task in completed
    ]
    parked_lines = [
        f"{inline_code(task['id'])}: {task.get('park_reason', task['gist'])} "
        f"Resume: {task.get('resume_condition', 'Recompute the node from its blocker evidence.')}"
        for task in parked
    ]
    return (
        "# Continuity\n\n"
        f"Canonical SHA-256: {inline_code(digest)}\n\n"
        f"Generation: {inline_code(plan['generation'])}\n\n"
        "## Resume here\n\n"
        f"{bullets(next_lines, 'The board has no active frontier; recompute before mutation.')}\n\n"
        "## Completed receipts\n\n"
        f"{bullets(completed_lines)}\n\n"
        "## Parked work\n\n"
        f"{bullets(parked_lines)}\n\n"
        "## Invariants\n\n"
        f"- {plan['scope_law']}\n"
        f"- {plan['hard_prerequisite']}\n"
        "- Update the canonical JSON, render, and pass check mode before committing a transition.\n"
    )


def render_disagreements(plan: dict[str, Any], digest: str) -> str:
    sections = []
    for decision in plan.get("decisions", []):
        sections.append(
            f"## {decision['id']}: {decision['question']}\n\n"
            f"Choice: {decision['choice']}\n\n"
            f"Reversibility: {inline_code(decision['reversibility_class'])}\n\n"
            f"Retraction: {decision['retraction_path']}\n"
        )
    return (
        "# Decisions and disagreements\n\n"
        f"Canonical SHA-256: {inline_code(digest)}\n\n"
        "These decisions resolve known design forks. A failed oracle reopens the named "
        "decision through its retraction path rather than weakening acceptance.\n\n"
        + "\n".join(sections)
    )


def render_lessons(plan: dict[str, Any], digest: str) -> str:
    fact_lines = [
        f"- {inline_code(fact['id'])}: {fact['text']}"
        for fact in plan.get("facts", [])
    ]
    exclusions = [f"- {item}" for item in plan.get("scope_exclusions", [])]
    return (
        "# Lessons and constraints\n\n"
        f"Canonical SHA-256: {inline_code(digest)}\n\n"
        "## Current facts\n\n"
        + "\n".join(fact_lines)
        + "\n\n"
        "## Explicit exclusions\n\n"
        + "\n".join(exclusions)
        + "\n"
    )


def render_replay(plan: dict[str, Any], digest: str) -> str:
    lines = []
    for task in plan["tasks"]:
        evidence = (
            "; ".join(task["discharge_evidence"])
            or task.get("park_reason")
            or "; ".join(task.get("progress_evidence", []))
            or "awaiting execution"
        )
        lines.append(
            f"- [{task_mark(task)}] {inline_code(task['id'])} "
            f"{task['status']}: {evidence}"
        )
    return (
        "# Execution replay\n\n"
        f"Canonical SHA-256: {inline_code(digest)}\n\n"
        "This is a generated status replay. Durable proof lives in each node's "
        "discharge evidence and the referenced external artifacts.\n\n"
        + "\n".join(lines)
        + "\n"
    )


def render_validation(plan: dict[str, Any], digest: str) -> str:
    work_count = sum(task["type"] in WORK_TYPES for task in plan["tasks"])
    verify_count = sum(task["type"] in VERIFY_TYPES for task in plan["tasks"])
    return (
        "# Board validation\n\n"
        f"Canonical SHA-256: {inline_code(digest)}\n\n"
        "- Canonical JSON parses.\n"
        "- Required fields, palettes, controllers, and statuses validate.\n"
        "- Dependency graph is acyclic and every task feeds the terminal node.\n"
        "- Portable binding has at most one active frontier and its dependencies are complete.\n"
        f"- {work_count} work nodes have verifier siblings.\n"
        f"- {verify_count} verifier nodes are independently controlled.\n"
        f"- {len(plan['acceptance_obligations'])} obligations have work and verifier coverage.\n"
        "- Completed nodes carry discharge evidence and live oracles forbid substitution.\n"
        "- Parallel work nodes have no exact declared-scope collision.\n"
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
        rendered[ROOT / "nodes" / f"{task['id']}.md"] = render_node(
            plan, task, digest
        )
    return rendered


def check_or_write(rendered: dict[Path, str], check: bool) -> int:
    expected_node_paths = {
        path for path in rendered if path.parent == ROOT / "nodes"
    }
    existing_node_paths = set((ROOT / "nodes").glob("*.md"))
    extra_paths = sorted(existing_node_paths - expected_node_paths)
    if check:
        drift = []
        for path, content in rendered.items():
            if not path.exists() or path.read_text() != content:
                drift.append(path.relative_to(ROOT))
        drift.extend(path.relative_to(ROOT) for path in extra_paths)
        if drift:
            for path in drift:
                print(f"projection drift: {path}", file=sys.stderr)
            return 1
        print(f"validated {len(rendered)} projections with no drift")
        return 0

    (ROOT / "nodes").mkdir(parents=True, exist_ok=True)
    for path, content in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    for path in extra_paths:
        path.unlink()
    print(f"rendered {len(rendered)} projections")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate projections without writing them",
    )
    args = parser.parse_args()
    plan, digest = load_plan()
    errors = validate(plan)
    if errors:
        for error in errors:
            print(f"invalid plan: {error}", file=sys.stderr)
        return 1
    return check_or_write(projections(plan, digest), args.check)


if __name__ == "__main__":
    raise SystemExit(main())
