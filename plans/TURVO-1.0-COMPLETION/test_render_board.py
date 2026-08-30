"""Check that portable proof reporting cannot silently turn a park into done."""

from copy import deepcopy
import unittest

from render_board import load_plan, render_node, render_replay, validate


class ParkReceiptTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.digest = load_plan()

    def parked_plan(self):
        plan = deepcopy(self.plan)
        task = plan["tasks"][0]
        task.update(
            status="parked",
            park_reason="Required native oracle failed.",
            resume_condition="The named public API becomes available.",
            discharge_evidence=[],
            progress_evidence=["Local unit check passed; native proof is missing."],
        )
        return plan, task

    def test_current_board_validates(self):
        self.assertEqual(validate(self.plan), [])

    def test_park_requires_reason(self):
        for invalid in (None, "", " ", ["not a string"]):
            with self.subTest(value=invalid):
                plan, task = self.parked_plan()
                task["park_reason"] = invalid
                self.assertIn(
                    f"{task['id']}: parked task needs park_reason", validate(plan)
                )

    def test_park_requires_observable_resume_condition(self):
        plan, task = self.parked_plan()
        del task["resume_condition"]
        self.assertIn(
            f"{task['id']}: parked task needs resume_condition", validate(plan)
        )

    def test_progress_does_not_discharge_a_completed_task(self):
        plan, task = self.parked_plan()
        task["status"] = "completed"
        self.assertIn(
            f"{task['id']}: completed task has no discharge evidence", validate(plan)
        )

    def test_node_distinguishes_progress_and_discharge(self):
        plan, task = self.parked_plan()
        rendered = render_node(plan, task, self.digest)
        self.assertIn(task["park_reason"], rendered)
        self.assertIn(task["resume_condition"], rendered)
        self.assertIn("Partial receipts (not discharge)", rendered)
        self.assertIn("Not yet discharged.", rendered)

    def test_replay_preserves_park_reason(self):
        plan, task = self.parked_plan()
        self.assertIn(task["park_reason"], render_replay(plan, self.digest))


if __name__ == "__main__":
    unittest.main()
