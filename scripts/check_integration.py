"""Verify the public integration's source pins, patch digests and lockfile family."""

import argparse
import hashlib
import json
import re
from pathlib import Path
import tomllib


FAMILIES = {
    "servo": {"servo", "servo-base", "servo-net-traits"},
    "tauri": {
        "tauri", "tauri-build", "tauri-codegen", "tauri-macros",
        "tauri-runtime", "tauri-runtime-wry", "tauri-utils",
    },
}


def verify_pins(manifest, integrations, lock=None):
    overrides = manifest.get("patch", {}).get("crates-io", {})
    for family, names in FAMILIES.items():
        integration = integrations[family]
        revision = integration["revision"]
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError(f"{family}: expected a full commit revision")
        repository = integration["repository"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError(f"{family}: invalid public repository name")
        git = f"https://github.com/{repository}"
        for name in names:
            override = overrides.get(name, {})
            if override.get("git") != git or override.get("rev") != revision:
                raise ValueError(f"{name}: manifest does not match the public integration pin")
        if lock is None:
            continue
        source = f"git+{git}?rev={revision}#{revision}"
        seen = set()
        for package in lock["package"]:
            name = package["name"]
            engine_member = (family == "servo" and name.startswith("servo-")
                             and package["version"] == "0.5.0")
            if name not in names and not engine_member:
                continue
            if package.get("source") != source:
                raise ValueError(f"{name}: mixed registry or other-revision integration dependency")
            seen.add(name)
        if missing := names - seen:
            raise ValueError(f"{family}: lockfile is missing {sorted(missing)}")


def check(root, metadata_only=False):
    integrations = {}
    for family in FAMILIES:
        directory = root / "patches" / family
        integration = json.loads((directory / "integration.json").read_text())
        for patch in integration["patches"]:
            path = directory / patch["path"]
            if path.resolve().parent != directory.resolve():
                raise ValueError(f"{family}: patch path leaves its integration directory")
            if hashlib.sha256(path.read_bytes()).hexdigest() != patch["sha256"]:
                raise ValueError(f"{family}: patch digest mismatch for {patch['path']}")
        integrations[family] = integration
    manifest = tomllib.loads((root / "Cargo.toml").read_text())
    lock = None if metadata_only else tomllib.loads((root / "Cargo.lock").read_text())
    verify_pins(manifest, integrations, lock)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    try:
        check(Path(__file__).resolve().parents[1], args.metadata_only)
    except (KeyError, OSError, ValueError) as error:
        parser.exit(1, f"integration verification failed: {error}\n")
    print("Public integration source pins and patch digests verified"
          + (" (lockfile not checked)" if args.metadata_only else "; lockfile family verified"))
