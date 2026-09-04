# ServoShell VS Code compatibility ledger

Status: capture pending.

This ledger is generated from a Firefox console export while the pinned Servo
fork renders code-server directly in ServoShell. The launcher captures the
initial and 15-second-idle screenshots, then keeps the runtime alive for the
operator-owned Firefox DevTools export.

## Reproduction

```sh
./scripts/vscode-ledger.sh --servo-checkout /path/to/Travis-Gilbert-servo /path/to/workspace
```

The Servo checkout must be clean, use the `Travis-Gilbert/servo` origin, and be
at the exact revision recorded in `patches/servo/integration.json`. The pinned
revision exposes DevTools unconditionally rather than through a Cargo feature;
the launcher detects that manifest shape and records the selected build mode.

After page load and the idle capture:

1. Open `about:debugging` in Firefox.
2. Add `localhost:6080` as a network location and connect.
3. Inspect the code-server target.
4. Export the console to
   `docs/ledgers/vscode/0001-servoshell-console.json`.
5. Return to the launcher and press Enter. It writes stable `VSC-NNN` classes
   to this file.

The export is intentionally not automated: Firefox attachment and its console
export are the operator receipt. For a non-interactive screenshot-only run,
pass `--no-wait-for-console`, then classify the later export with:

```sh
python3 scripts/vscode-ledger-classify.py docs/ledgers/vscode/0001-servoshell-console.json
```

Expected image paths are `0001-servoshell-load.png` and
`0001-servoshell-idle.png`. Neither image nor a console class is claimed until
the native capture has actually run.
