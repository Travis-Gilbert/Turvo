import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("vscode-ledger-classify.py")


class VscodeLedgerClassifierTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="turvo-vscode-ledger-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.console = self.directory / "console.json"
        self.output = self.directory / "ledger.md"
        self.metadata = self.directory / "missing-metadata.json"

    def run_classifier(self, *extra):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--output",
                str(self.output),
                "--metadata",
                str(self.metadata),
                *extra,
                str(self.console),
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def write(self, value):
        self.console.write_text(json.dumps(value), encoding="utf-8")

    def test_groups_by_normalized_source_and_first_line(self):
        self.write(
            [
                {
                    "level": "error",
                    "filename": "http://127.0.0.1:8080/out/main.js?v=1",
                    "lineNumber": 10,
                    "message": "Webview failed?token=secret\nstack A",
                },
                {
                    "level": "error",
                    "filename": "http://127.0.0.1:8080/out/main.js?v=2",
                    "lineNumber": 11,
                    "message": "Webview failed?token=different\nstack B",
                },
                {"level": "info", "filename": "main.js", "message": "ready"},
            ]
        )
        result = self.run_classifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        ledger = self.output.read_text(encoding="utf-8")
        self.assertIn("Classified failure classes: 1", ledger)
        self.assertIn("Occurrences: 2", ledger)
        self.assertIn("Webview failed?token=[REDACTED]", ledger)
        self.assertNotIn("stack A", ledger)
        self.assertNotIn("ready", ledger)

    def test_reuses_ids_when_a_new_earlier_class_appears(self):
        self.write([{"level": "error", "source": "z.js", "message": "existing"}])
        first = self.run_classifier()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("### VSC-001", self.output.read_text(encoding="utf-8"))

        self.write(
            [
                {"level": "error", "source": "a.js", "message": "new"},
                {"level": "error", "source": "z.js", "message": "existing"},
            ]
        )
        second = self.run_classifier()
        self.assertEqual(second.returncode, 0, second.stderr)
        ledger = self.output.read_text(encoding="utf-8")
        self.assertRegex(ledger, r"### VSC-001[\s\S]+First message line: <code>existing</code>")
        self.assertRegex(ledger, r"### VSC-002[\s\S]+First message line: <code>new</code>")

    def test_accepts_nested_firefox_messages_and_json_lines(self):
        entries = [
            {
                "type": "consoleAPICall",
                "message": {
                    "level": "error",
                    "filename": "file:///work/pre/index.html",
                    "arguments": ["service worker", "unavailable"],
                },
            },
            {"severity": "warning", "url": "https://host/a.js#x", "text": "fallback"},
        ]
        self.console.write_text("\n".join(json.dumps(entry) for entry in entries), encoding="utf-8")
        result = self.run_classifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        ledger = self.output.read_text(encoding="utf-8")
        self.assertIn("Classified failure classes: 2", ledger)
        self.assertIn("service worker unavailable", ledger)
        self.assertIn("https://host/a.js", ledger)

    def test_invalid_export_does_not_overwrite_existing_ledger(self):
        self.output.write_text("existing ledger\n", encoding="utf-8")
        self.console.write_text("not json\n", encoding="utf-8")
        result = self.run_classifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "existing ledger\n")

    def test_turvo_profile_renders_its_native_exercise_and_command(self):
        self.write([])
        self.metadata.write_text(
            json.dumps(
                {
                    "profile": "turvo",
                    "reproduction_command": [
                        "./scripts/vscode-turvo-ledger.sh",
                        "/tmp/work space",
                    ],
                }
            ),
            encoding="utf-8",
        )
        result = self.run_classifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        ledger = self.output.read_text(encoding="utf-8")
        self.assertIn("# Turvo VS Code compatibility ledger", ledger)
        self.assertIn("buffer edit, terminal echo", ledger)
        self.assertIn("./scripts/vscode-turvo-ledger.sh '/tmp/work space'", ledger)


if __name__ == "__main__":
    unittest.main()
