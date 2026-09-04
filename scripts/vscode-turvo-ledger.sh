#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SCRIPT_DIR
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
readonly REPO_ROOT
readonly INTEGRATION_FILE="${REPO_ROOT}/patches/servo/integration.json"
readonly LEDGER_DIR="${REPO_ROOT}/docs/ledgers/vscode"
readonly REPORT_DIR="${REPO_ROOT}/.reports/vscode"

code_server_url=""
console_export="${LEDGER_DIR}/0002-turvo-console.json"
devtools_port="6080"
workspace="${REPO_ROOT}"

usage() {
  cat <<'EOF'
Usage: scripts/vscode-turvo-ledger.sh [options] [workspace]

Launch the Turvo code-server example, expose its loopback Firefox DevTools
endpoint, and classify the operator-exported console into 0002-turvo.md.

Options:
  --code-server-url URL  Use an already-running loopback code-server
  --devtools-port PORT   Firefox remote DevTools port (default: 6080)
  --console PATH         Firefox JSON export path
  -h, --help             Show this help

Without --code-server-url, the target-suffixed code-server sidecar must exist
under examples/code-server/binaries/.
EOF
}

die() {
  printf 'vscode-turvo-ledger: %s\n' "$*" >&2
  exit 1
}

require_argument() {
  (($# >= 2)) || die "$1 requires a value"
}

while (($#)); do
  case "$1" in
    --code-server-url)
      require_argument "$@"
      code_server_url="$2"
      shift 2
      ;;
    --devtools-port)
      require_argument "$@"
      devtools_port="$2"
      shift 2
      ;;
    --console)
      require_argument "$@"
      console_export="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      die "unknown option: $1"
      ;;
    *)
      workspace="$1"
      shift
      (($# == 0)) || die "only one workspace path may be supplied"
      ;;
  esac
done

command -v cargo >/dev/null || die "cargo is required"
command -v python3 >/dev/null || die "python3 is required"
command -v rustc >/dev/null || die "rustc is required"
[[ -f "${INTEGRATION_FILE}" ]] || die "missing Servo integration descriptor: ${INTEGRATION_FILE}"
servo_revision="$(python3 - "${INTEGRATION_FILE}" <<'PY'
import json
import pathlib
import sys

value = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
revision = value.get("revision", "")
if not isinstance(revision, str) or len(revision) != 40 or any(
    character not in "0123456789abcdef" for character in revision
):
    raise SystemExit("integration revision is not a full lowercase Git SHA")
print(revision)
PY
)" || die "could not read the pinned Servo revision"
if [[ ! "${devtools_port}" =~ ^[0-9]+$ ]] ||
  ((devtools_port < 1 || devtools_port > 65535)); then
  die "invalid DevTools port: ${devtools_port}"
fi
workspace="$(cd -- "${workspace}" 2>/dev/null && pwd -P)" || die "workspace is not a directory"

if [[ -n "${code_server_url}" ]]; then
  [[ "${code_server_url}" =~ ^http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]+(/.*)?$ ]] ||
    die "--code-server-url must be an explicit loopback HTTP URL"
else
  host_triple="$(rustc --print host-tuple)"
  sidecar="${REPO_ROOT}/examples/code-server/binaries/code-server-${host_triple}"
  [[ -x "${sidecar}" ]] ||
    die "missing executable sidecar ${sidecar}; provision the hard-fork binary or pass --code-server-url"
fi

python3 - "${devtools_port}" <<'PY' || exit 1
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
    try:
        listener.bind(("127.0.0.1", port))
    except OSError as error:
        raise SystemExit(f"DevTools port 127.0.0.1:{port} is unavailable: {error}")
PY

mkdir -p -- "${LEDGER_DIR}" "${REPORT_DIR}" "$(dirname -- "${console_export}")"
console_export="$(cd -- "$(dirname -- "${console_export}")" && pwd -P)/$(basename -- "${console_export}")"
console_before="$(python3 - "${console_export}" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if path.is_file():
    stat = path.stat()
    print(f"{stat.st_mtime_ns}:{stat.st_size}")
else:
    print("missing")
PY
)"

readonly app_log="${REPORT_DIR}/0002-turvo.log"
readonly metadata_file="${REPORT_DIR}/0002-turvo-run.json"
app_pid=""

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if [[ -n "${app_pid}" ]] &&
    { kill -0 -- "-${app_pid}" 2>/dev/null || kill -0 "${app_pid}" 2>/dev/null; }; then
    kill -- "-${app_pid}" 2>/dev/null || kill "${app_pid}" 2>/dev/null || true
    wait "${app_pid}" 2>/dev/null || true
  fi
  exit "${exit_code}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

launch=(env "TURVO_DEVTOOLS_PORT=${devtools_port}" "TURVO_CODE_SERVER_WORKSPACE=${workspace}")
if [[ -n "${code_server_url}" ]]; then
  launch+=("TURVO_CODE_SERVER_URL=${code_server_url}")
fi
launch+=(cargo run -p turvo-code-server --locked)

(
  cd -- "${REPO_ROOT}"
  exec python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' "${launch[@]}"
) >"${app_log}" 2>&1 &
app_pid=$!

devtools_ready=0
for ((attempt = 1; attempt <= 120; attempt++)); do
  if python3 - "${devtools_port}" <<'PY'
import socket
import sys

with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=0.25):
    pass
PY
  then
    devtools_ready=1
    break
  fi
  kill -0 "${app_pid}" 2>/dev/null || die "Turvo exited; inspect ${app_log}"
  sleep 1
done
((devtools_ready == 1)) || die "Turvo DevTools did not listen on 127.0.0.1:${devtools_port}"

python3 - "${metadata_file}" "${workspace}" "${devtools_port}" "${code_server_url}" "${servo_revision}" <<'PY'
import json
import pathlib
import sys

destination = pathlib.Path(sys.argv[1])
workspace = sys.argv[2]
port = int(sys.argv[3])
server = sys.argv[4]
servo_revision = sys.argv[5]
command = ["./scripts/vscode-turvo-ledger.sh"]
if server:
    command.extend(["--code-server-url", server])
command.extend(["--devtools-port", str(port), workspace])
value = {
    "profile": "turvo",
    "workspace": workspace,
    "devtools_port": port,
    "servo_revision": servo_revision,
    "code_server_url": server or "bundled sidecar",
    "build_mode": "Turvo code-server example",
    "reproduction_command": command,
}
destination.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

printf '\nFirefox console export is an operator receipt:\n'
printf '  1. Open about:debugging and connect to localhost:%s.\n' "${devtools_port}"
printf '  2. Confirm the workbench renders, edit a buffer, and run: echo TURVO_CODE_SERVER_OK\n'
printf '  3. Open Markdown preview and one extension webview.\n'
printf '  4. Confirm the console has no webview serviceWorker.register attempt.\n'
printf '  5. Export the console as: %s\n' "${console_export}"
[[ -t 0 ]] || die "interactive stdin is required for the native exercise and console export"
read -r -p 'Press Enter after the native exercise and console export... '
[[ -s "${console_export}" ]] || die "console export is missing or empty: ${console_export}"
console_after="$(python3 - "${console_export}" <<'PY'
import pathlib
import sys

stat = pathlib.Path(sys.argv[1]).stat()
print(f"{stat.st_mtime_ns}:{stat.st_size}")
PY
)"
[[ "${console_after}" != "${console_before}" ]] ||
  die "console export was not updated during this capture: ${console_export}"

python3 "${SCRIPT_DIR}/vscode-ledger-classify.py" \
  --metadata "${metadata_file}" \
  --output "${LEDGER_DIR}/0002-turvo.md" \
  "${console_export}"
printf 'Turvo VS Code ledger capture complete.\n'
