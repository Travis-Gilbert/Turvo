import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from import_ledger import LedgerError, build_plan, parse_ledger, parse_ownership
from render_board import validate


ROOT = Path(__file__).resolve().parent
IMPORTER = ROOT / "import_ledger.py"


def ledger(classes):
    sections = []
    for class_id, source, message in classes:
        fingerprint = hashlib.sha256(f"{source}\0{message}".encode()).hexdigest()
        sections.extend(
            [
                f"### {class_id}",
                "",
                f"<!-- vscode-ledger-class: {class_id} fingerprint: {fingerprint} -->",
                f"- Source: <code>{source}</code>",
                f"- First message line: <code>{message}</code>",
                "",
            ]
        )
    return "\n".join(
        [
            "# Turvo VS Code compatibility ledger",
            "",
            f"- Classified failure classes: {len(classes)}",
            "",
            "## Failure classes",
            "",
            *sections,
        ]
    )


class LedgerPlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="turvo-ledger-plan-test-")
        self.addCleanup(self.temporary.cleanup)
        self.ledger_path = Path(self.temporary.name) / "0002-turvo.md"
        self.template = json.loads((ROOT / "plan-template.json").read_text())
        self.ownership = {
            "default_owner": "turvo",
            "default_owner_reason": "integration triage",
            "overrides": {},
        }

    def build(self, classes):
        self.ledger_path.write_text(ledger(classes), encoding="utf-8")
        capture = parse_ledger(self.ledger_path)
        routes = parse_ownership(capture, self.ownership)
        return capture, build_plan(self.template, capture, routes, self.ledger_path)

    def test_missing_capture_creates_no_failure_nodes(self):
        capture = parse_ledger(self.ledger_path)
        routes = parse_ownership(capture, self.ownership)
        plan = build_plan(self.template, capture, routes, self.ledger_path)
        self.assertEqual(capture.status, "capture_pending")
        self.assertFalse([task for task in plan["tasks"] if task.get("failure_class")])
        self.assertEqual(validate(plan), [])

    def test_one_work_and_verifier_per_observed_class(self):
        _, plan = self.build(
            [
                ("VSC-001", "pre/index.html", "service worker unavailable"),
                ("VSC-002", "workbench.js", "pointer capture failed"),
            ]
        )
        work = [task for task in plan["tasks"] if task["type"] == "work.implementation"]
        verify = [task for task in plan["tasks"] if task.get("failure_class") and task["type"] == "verify.live"]
        self.assertEqual(len(work), 2)
        self.assertEqual(len(verify), 2)
        self.assertEqual({task["owner"] for task in work + verify}, {"turvo"})
        self.assertEqual(validate(plan), [])

    def test_fingerprint_locked_override_sets_owner_and_dependency(self):
        self.ledger_path.write_text(
            ledger(
                [
                    ("VSC-001", "pre/index.html", "service worker unavailable"),
                    ("VSC-002", "workbench.js", "renderer missing"),
                ]
            ),
            encoding="utf-8",
        )
        capture = parse_ledger(self.ledger_path)
        first = capture.classes[0]
        second = capture.classes[1]
        self.ownership["overrides"] = {
            second.class_id: {
                "fingerprint": second.fingerprint,
                "owner": "servo-fork",
                "depends_on": [first.class_id],
                "reason": "native diagnosis routes this to Servo",
            }
        }
        routes = parse_ownership(capture, self.ownership)
        plan = build_plan(self.template, capture, routes, self.ledger_path)
        task = next(task for task in plan["tasks"] if task["id"] == "W_VSC_002")
        self.assertEqual(task["owner"], "servo-fork")
        self.assertIn("V_VSC_001", task["depends_on"])
        self.assertEqual(validate(plan), [])

    def test_override_rejects_stale_fingerprint(self):
        self.ledger_path.write_text(
            ledger([("VSC-001", "pre/index.html", "service worker unavailable")]),
            encoding="utf-8",
        )
        capture = parse_ledger(self.ledger_path)
        self.ownership["overrides"] = {
            "VSC-001": {
                "fingerprint": "0" * 64,
                "owner": "code-server-fork",
            }
        }
        with self.assertRaisesRegex(LedgerError, "fingerprint does not match"):
            parse_ownership(capture, self.ownership)

    def test_resolved_class_may_leave_historical_ownership_override(self):
        self.ledger_path.write_text(ledger([]), encoding="utf-8")
        capture = parse_ledger(self.ledger_path)
        self.ownership["overrides"] = {
            "VSC-001": {
                "fingerprint": "0" * 64,
                "owner": "code-server-fork",
            }
        }
        self.assertEqual(parse_ownership(capture, self.ownership), {})

    def test_declared_count_must_match_sections(self):
        self.ledger_path.write_text(
            ledger([("VSC-001", "a.js", "broken")]).replace(
                "Classified failure classes: 1", "Classified failure classes: 2"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(LedgerError, "declares 2 classes"):
            parse_ledger(self.ledger_path)

    def test_absence_requires_completed_capture(self):
        result = subprocess.run(
            [sys.executable, str(IMPORTER), "--ledger", str(self.ledger_path), "--assert-absent", "VSC-001"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("completed native capture", result.stderr)

    def test_assert_empty_accepts_explicit_zero_class_capture(self):
        self.ledger_path.write_text(ledger([]), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(IMPORTER), "--ledger", str(self.ledger_path), "--assert-empty"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
