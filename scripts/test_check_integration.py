import copy
import unittest

from check_integration import FAMILIES, verify_pins


class IntegrationPinsTests(unittest.TestCase):
    def setUp(self):
        self.integrations = {
            family: {"repository": f"owner/{family}", "revision": character * 40}
            for family, character in [("servo", "a"), ("tauri", "b")]
        }
        overrides = {}
        packages = []
        for family, names in FAMILIES.items():
            integration = self.integrations[family]
            git = "https://github.com/" + integration["repository"]
            revision = integration["revision"]
            for name in names:
                overrides[name] = {"git": git, "rev": revision}
                packages.append({"name": name, "version": "0.5.0",
                                 "source": f"git+{git}?rev={revision}#{revision}"})
        self.manifest = {"patch": {"crates-io": overrides}}
        self.lock = {"package": packages}

    def test_coherent_public_family(self):
        verify_pins(self.manifest, self.integrations, self.lock)

    def test_rejects_branch_instead_of_exact_revision(self):
        self.integrations["servo"]["revision"] = "main"
        with self.assertRaisesRegex(ValueError, "full commit"):
            verify_pins(self.manifest, self.integrations)

    def test_rejects_manifest_drift(self):
        self.manifest["patch"]["crates-io"]["tauri-runtime"]["rev"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "tauri-runtime: manifest"):
            verify_pins(self.manifest, self.integrations)

    def test_rejects_registry_copy_of_transitive_engine_crate(self):
        self.lock["package"].append({"name": "servo-config", "version": "0.5.0",
                                     "source": "registry+https://github.com/rust-lang/crates.io-index"})
        with self.assertRaisesRegex(ValueError, "servo-config: mixed"):
            verify_pins(self.manifest, self.integrations, self.lock)

    def test_rejects_duplicate_other_revision(self):
        package = copy.deepcopy(self.lock["package"][0])
        package["source"] += "different"
        self.lock["package"].append(package)
        with self.assertRaisesRegex(ValueError, "mixed registry or other-revision"):
            verify_pins(self.manifest, self.integrations, self.lock)

    def test_rejects_missing_locked_crate(self):
        self.lock["package"] = [p for p in self.lock["package"] if p["name"] != "servo"]
        with self.assertRaisesRegex(ValueError, "lockfile is missing"):
            verify_pins(self.manifest, self.integrations, self.lock)


if __name__ == "__main__":
    unittest.main()
