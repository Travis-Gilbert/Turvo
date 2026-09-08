# Turvo VS Code compatibility ledger

Status: native capture pending.

This ledger is generated from a Firefox console export while the Turvo
`examples/code-server` app renders the hard-fork code-server workbench. Source
wiring and patch replay are not substitutes for this native receipt.

## Reproduction

With a target-suffixed hard-fork sidecar provisioned:

```sh
./scripts/vscode-turvo-ledger.sh /path/to/workspace
```

An already-running loopback server can be selected with
`--code-server-url http://127.0.0.1:8080`. The launcher waits for Turvo's
DevTools endpoint, then asks the operator to render the workbench, edit a
buffer, echo `TURVO_CODE_SERVER_OK` in a terminal, render Markdown preview and
an extension webview, and export the console.

No `VSC-NNN` class is recorded here until that native exercise has run. The
expected absence of a webview `navigator.serviceWorker.register` call likewise
remains an open runtime oracle, even though the code-server patch stack forces
the no-service-worker branch when `window.__TURVO__` is present.
