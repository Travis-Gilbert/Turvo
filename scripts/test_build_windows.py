"""The staging protocol is testable without compiling Servo or loading a DLL."""

from pathlib import Path
import tempfile
import unittest

from build_windows import ANGLE_LIBRARIES, stage_angle


class AngleStagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="turvo-staging-test-")
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "target" / "windows-target" / "debug"

    def make_output(self, profile, label, complete=True):
        output = profile / "build" / label / "out"
        output.mkdir(parents=True)
        for name in ANGLE_LIBRARIES if complete else ANGLE_LIBRARIES[:1]:
            (output / name).write_bytes((label + name).encode())
        return output

    def test_copies_only_the_current_cargo_output(self):
        current = self.make_output(self.profile, "mozangle-current")
        self.make_output(self.profile, "mozangle-stale")
        stage_angle({current}, self.profile)
        for name in ANGLE_LIBRARIES:
            for directory in (self.profile, self.profile / "deps"):
                self.assertEqual((directory / name).read_bytes(), (current / name).read_bytes())

    def test_rejects_incomplete_outputs(self):
        partial = self.make_output(self.profile, "mozangle-partial", complete=False)
        with self.assertRaisesRegex(RuntimeError, "got 0"):
            stage_angle({partial}, self.profile)

    def test_rejects_ambiguous_current_outputs(self):
        outputs = {self.make_output(self.profile, name) for name in ("mozangle-a", "mozangle-b")}
        with self.assertRaisesRegex(RuntimeError, "got 2"):
            stage_angle(outputs, self.profile)

    def test_does_not_stage_host_libraries_into_a_cross_target(self):
        host = self.make_output(self.profile.parent.parent / "debug", "mozangle-host")
        with self.assertRaisesRegex(RuntimeError, "got 0"):
            stage_angle({host}, self.profile)


if __name__ == "__main__":
    unittest.main()
