# Turvo code-server experiment

This example loads a code-server workbench in a Turvo window. When
`TURVO_CODE_SERVER_URL` is set, Turvo connects to that server and does not
spawn a process. When it is unset, the example starts the bundled
`code-server` sidecar on loopback and opens `http://127.0.0.1:8080`.
The configured URL must be uncredentialed loopback HTTP because Turvo uses it
as the private target for its allowlisted VS Code resource interception.

Provision the hard-fork binary before building the sidecar path:

The V4 patch stack is pinned by commit
`fbe63cdbad0fab6bd80ef6f8b671725646edd61b` on the fork branch
`turvo/webviews-1.0`.

```sh
target_triple="$(rustc --print host-tuple)"
cp /path/to/code-server "examples/code-server/binaries/code-server-${target_triple}"
cargo run -p turvo-code-server --locked
```

The sidecar opens the directory named by `TURVO_CODE_SERVER_WORKSPACE`, or the
current directory when that variable is unset. A separately managed server can
be used instead:

```sh
TURVO_CODE_SERVER_URL=http://127.0.0.1:8080 \
  cargo run -p turvo-code-server --locked
```

The remote workbench is not granted shell-plugin permissions. The Rust host
owns sidecar launch and shutdown, and the window-title callback copies the
workbench document title into the native window. Turvo claims only VS Code's
`*.vscode-cdn.net` webview documents and
`*.vscode-resource.vscode-cdn.net` resources; those requests cannot fall
through to the public network when the proxy is enabled.
