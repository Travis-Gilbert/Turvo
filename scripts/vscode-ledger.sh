#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SCRIPT_DIR
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
readonly REPO_ROOT
readonly INTEGRATION_FILE="${REPO_ROOT}/patches/servo/integration.json"
readonly LEDGER_DIR="${REPO_ROOT}/docs/ledgers/vscode"
readonly REPORT_DIR="${REPO_ROOT}/.reports/vscode"

servo_checkout="$(cd -- "${REPO_ROOT}/.." && pwd -P)/servo"
code_server_bin="code-server"
code_server_addr="127.0.0.1:8080"
devtools_port="6080"
webdriver_port="7000"
console_export="${LEDGER_DIR}/0001-servoshell-console.json"
idle_seconds="15"
skip_build=0
wait_for_console=1
workspace="${REPO_ROOT}"

usage() {
  cat <<'EOF'
Usage: scripts/vscode-ledger.sh [options] [workspace]

Build the exact Turvo-pinned ServoShell, launch code-server and ServoShell,
capture WebDriver screenshots, and hold the processes open for Firefox console
export and deterministic ledger classification.

Options:
  --servo-checkout PATH  Exact, clean Travis-Gilbert/servo checkout (default: ../servo)
  --code-server PATH     code-server executable (default: code-server from PATH)
  --bind-addr HOST:PORT  code-server loopback address (default: 127.0.0.1:8080)
  --devtools-port PORT   Firefox remote DevTools port (default: 6080)
  --webdriver-port PORT  Servo WebDriver port (default: 7000)
  --console PATH         Firefox JSON export path
  --idle-seconds N       Delay between screenshots (default: 15)
  --skip-build           Reuse an existing build after all source checks
  --no-wait-for-console  Stop after screenshots; leave classification pending
  -h, --help             Show this help
EOF
}

die() {
  printf 'vscode-ledger: %s\n' "$*" >&2
  exit 1
}

require_argument() {
  (($# >= 2)) || die "$1 requires a value"
}

while (($#)); do
  case "$1" in
    --servo-checkout)
      require_argument "$@"
      servo_checkout="$2"
      shift 2
      ;;
    --code-server)
      require_argument "$@"
      code_server_bin="$2"
      shift 2
      ;;
    --bind-addr)
      require_argument "$@"
      code_server_addr="$2"
      shift 2
      ;;
    --devtools-port)
      require_argument "$@"
      devtools_port="$2"
      shift 2
      ;;
    --webdriver-port)
      require_argument "$@"
      webdriver_port="$2"
      shift 2
      ;;
    --console)
      require_argument "$@"
      console_export="$2"
      shift 2
      ;;
    --idle-seconds)
      require_argument "$@"
      idle_seconds="$2"
      shift 2
      ;;
    --skip-build)
      skip_build=1
      shift
      ;;
    --no-wait-for-console)
      wait_for_console=0
      shift
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

command -v git >/dev/null || die "git is required"
command -v curl >/dev/null || die "curl is required"
command -v python3 >/dev/null || die "python3 is required"
[[ -f "${INTEGRATION_FILE}" ]] || die "missing Servo integration descriptor: ${INTEGRATION_FILE}"
[[ "${code_server_addr}" =~ ^127\.0\.0\.1:([0-9]+)$ ]] ||
  die "--bind-addr must use 127.0.0.1 and an explicit port"
code_server_port="${BASH_REMATCH[1]}"
for port in "${code_server_port}" "${devtools_port}" "${webdriver_port}"; do
  if [[ ! "${port}" =~ ^[0-9]+$ ]] || ((port < 1 || port > 65535)); then
    die "invalid TCP port: ${port}"
  fi
done
[[ "${code_server_port}" != "${devtools_port}" &&
   "${code_server_port}" != "${webdriver_port}" &&
   "${devtools_port}" != "${webdriver_port}" ]] || die "all three ports must be distinct"
[[ "${idle_seconds}" =~ ^[0-9]+$ ]] || die "--idle-seconds must be a non-negative integer"

workspace="$(cd -- "${workspace}" 2>/dev/null && pwd -P)" || die "workspace is not a directory"
servo_checkout="$(cd -- "${servo_checkout}" 2>/dev/null && pwd -P)" ||
  die "Servo checkout does not exist; pass --servo-checkout with a clean Travis-Gilbert/servo checkout"
console_parent="$(dirname -- "${console_export}")"
mkdir -p -- "${LEDGER_DIR}" "${REPORT_DIR}" "${console_parent}"
console_export="$(cd -- "${console_parent}" && pwd -P)/$(basename -- "${console_export}")"
console_export_before="$(python3 - "${console_export}" <<'PY'
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

IFS=$'\t' read -r expected_repository expected_revision < <(
  python3 - "${INTEGRATION_FILE}" <<'PY'
import json
import pathlib
import sys

value = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
print(value["repository"], value["revision"], sep="\t")
PY
)
readonly expected_repository expected_revision
[[ "${expected_repository}" == "Travis-Gilbert/servo" ]] ||
  die "integration descriptor points at unexpected fork: ${expected_repository}"
[[ "${expected_revision}" =~ ^[0-9a-f]{40}$ ]] || die "integration revision is not a full Git SHA"

[[ "$(git -C "${servo_checkout}" rev-parse --is-inside-work-tree 2>/dev/null)" == "true" ]] ||
  die "Servo path is not a Git checkout: ${servo_checkout}"
actual_revision="$(git -C "${servo_checkout}" rev-parse HEAD)"
[[ "${actual_revision}" == "${expected_revision}" ]] ||
  die "Servo checkout is ${actual_revision}; expected ${expected_revision}"
remote_url="$(git -C "${servo_checkout}" remote get-url origin 2>/dev/null)" ||
  die "Servo checkout has no origin remote"
case "${remote_url}" in
  https://github.com/Travis-Gilbert/servo|https://github.com/Travis-Gilbert/servo.git|git@github.com:Travis-Gilbert/servo.git|ssh://git@github.com/Travis-Gilbert/servo.git)
    ;;
  *)
    die "Servo origin is not the product fork: ${remote_url}"
    ;;
esac
[[ -z "$(git -C "${servo_checkout}" status --porcelain)" ]] ||
  die "Servo checkout must be clean so the capture is attributable to the pinned revision"
[[ -x "${servo_checkout}/mach" ]] || die "Servo checkout has no executable ./mach"

if [[ "${code_server_bin}" == */* ]]; then
  code_server_bin="$(cd -- "$(dirname -- "${code_server_bin}")" 2>/dev/null && pwd -P)/$(basename -- "${code_server_bin}")" ||
    die "code-server path does not exist"
  [[ -x "${code_server_bin}" ]] || die "code-server is not executable: ${code_server_bin}"
else
  code_server_bin="$(command -v "${code_server_bin}")" || die "code-server is not installed or not on PATH"
fi

port_available() {
  python3 - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
    listener.bind(("127.0.0.1", port))
PY
}

for port in "${code_server_port}" "${devtools_port}" "${webdriver_port}"; do
  port_available "${port}" || die "127.0.0.1:${port} is already in use"
done

has_devtools_feature="$({
  python3 - "${servo_checkout}/ports/servoshell/Cargo.toml" <<'PY'
import pathlib
import sys
import tomllib

manifest = tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if "devtools" in manifest.get("features", {}) else 1)
PY
} && printf yes || printf no)"
build_command=("${servo_checkout}/mach" build)
if [[ "${has_devtools_feature}" == "yes" ]]; then
  build_command+=(--features devtools)
  build_mode="explicit servoshell devtools feature"
else
  build_mode="pinned servoshell with unconditional devtools dependency"
fi
printf 'Servo build mode: %s\n' "${build_mode}"
printf 'Servo revision: %s\n' "${expected_revision}"
if ((skip_build == 0)); then
  (cd -- "${servo_checkout}" && "${build_command[@]}")
else
  printf 'Skipping Servo build by explicit request.\n'
fi

folder_query="$(python3 - "${workspace}" <<'PY'
import sys
from urllib.parse import quote

print(quote(sys.argv[1], safe=""))
PY
)"
readonly code_server_url="http://${code_server_addr}"
readonly workbench_url="${code_server_url}/?folder=${folder_query}"
readonly webdriver_url="http://127.0.0.1:${webdriver_port}"
readonly code_server_log="${REPORT_DIR}/0001-servoshell-code-server.log"
readonly servoshell_log="${REPORT_DIR}/0001-servoshell.log"
readonly metadata_file="${REPORT_DIR}/0001-servoshell-run.json"
code_server_pid=""
servoshell_pid=""
session_id=""

cleanup() {
  local exit_code=$?
  local attempt
  local pid
  trap - EXIT INT TERM
  if [[ -n "${session_id}" ]]; then
    curl --silent --show-error --max-time 2 --request DELETE \
      "${webdriver_url}/session/${session_id}" >/dev/null 2>&1 || true
  fi
  for pid in "${servoshell_pid}" "${code_server_pid}"; do
    if [[ -n "${pid}" ]] &&
      { kill -0 -- "-${pid}" 2>/dev/null || kill -0 "${pid}" 2>/dev/null; }; then
      kill -- "-${pid}" 2>/dev/null || kill "${pid}" 2>/dev/null || true
      for ((attempt = 1; attempt <= 25; attempt++)); do
        kill -0 -- "-${pid}" 2>/dev/null || break
        sleep 0.2
      done
      kill -KILL -- "-${pid}" 2>/dev/null || true
      wait "${pid}" 2>/dev/null || true
    fi
  done
  exit "${exit_code}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

python3 -c 'import os, sys; os.setsid(); os.execv(sys.argv[1], sys.argv[1:])' \
  "${code_server_bin}" --auth none --bind-addr "${code_server_addr}" "${workspace}" \
  >"${code_server_log}" 2>&1 &
code_server_pid=$!

wait_for_http() {
  local url="$1"
  local pid="$2"
  local label="$3"
  local attempt
  for ((attempt = 1; attempt <= 120; attempt++)); do
    if curl --silent --fail --max-time 2 --output /dev/null "${url}"; then
      return 0
    fi
    kill -0 "${pid}" 2>/dev/null || die "${label} exited; inspect ${REPORT_DIR}"
    sleep 1
  done
  die "timed out waiting for ${label} at ${url}"
}

wait_for_http "${code_server_url}/healthz" "${code_server_pid}" "code-server"
(
  cd -- "${servo_checkout}"
  exec python3 -c 'import os, sys; os.setsid(); os.execv(sys.argv[1], sys.argv[1:])' \
    "${servo_checkout}/mach" run \
    "--devtools=${devtools_port}" "--webdriver=${webdriver_port}" "${workbench_url}"
) >"${servoshell_log}" 2>&1 &
servoshell_pid=$!
wait_for_http "${webdriver_url}/status" "${servoshell_pid}" "Servo WebDriver"

session_response="$(
  curl --silent --show-error --fail --max-time 30 \
    --header 'Content-Type: application/json' \
    --request POST \
    --data '{"capabilities":{"alwaysMatch":{"browserName":"servo"}}}' \
    "${webdriver_url}/session"
)" || die "failed to create a Servo WebDriver session"
session_id="$(python3 -c '
import json, sys
value = json.load(sys.stdin)
payload = value.get("value", value)
print(payload.get("sessionId", value.get("sessionId", "")))
' <<<"${session_response}")"
[[ -n "${session_id}" ]] || die "Servo WebDriver did not return a session id"

document_ready=0
for ((attempt = 1; attempt <= 120; attempt++)); do
  ready_response="$(
    curl --silent --show-error --max-time 5 \
      --header 'Content-Type: application/json' \
      --request POST \
      --data '{"script":"return document.readyState","args":[]}' \
      "${webdriver_url}/session/${session_id}/execute/sync"
  )" || true
  if python3 -c 'import json, sys; raise SystemExit(0 if json.load(sys.stdin).get("value") == "complete" else 1)' \
    <<<"${ready_response}"; then
    document_ready=1
    break
  fi
  kill -0 "${servoshell_pid}" 2>/dev/null || die "ServoShell exited before page load"
  sleep 1
done
((document_ready == 1)) || die "workbench did not reach document.readyState=complete"

capture_screenshot() {
  local destination="$1"
  local temporary
  temporary="${REPORT_DIR}/$(basename -- "${destination}").tmp"
  curl --silent --show-error --fail --max-time 30 \
    "${webdriver_url}/session/${session_id}/screenshot" |
    python3 -c '
import base64, json, sys
value = json.load(sys.stdin).get("value")
if not isinstance(value, str):
    raise SystemExit("WebDriver screenshot response did not contain base64 data")
decoded = base64.b64decode(value, validate=True)
if not decoded.startswith(b"\x89PNG\r\n\x1a\n"):
    raise SystemExit("WebDriver screenshot response was not a PNG")
sys.stdout.buffer.write(decoded)
' >"${temporary}"
  [[ -s "${temporary}" ]] || die "WebDriver produced an empty screenshot: ${destination}"
  mv -- "${temporary}" "${destination}"
}

readonly load_screenshot="${LEDGER_DIR}/0001-servoshell-load.png"
readonly idle_screenshot="${LEDGER_DIR}/0001-servoshell-idle.png"
capture_screenshot "${load_screenshot}"
sleep "${idle_seconds}"
capture_screenshot "${idle_screenshot}"

python3 - "${metadata_file}" "${servo_checkout}" "${workspace}" "${expected_revision}" \
  "${code_server_addr}" "${devtools_port}" "${webdriver_port}" "${idle_seconds}" \
  "${build_mode}" "${workbench_url}" <<'PY'
import datetime
import json
import pathlib
import sys

destination = pathlib.Path(sys.argv[1])
value = {
    "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "servo_checkout": sys.argv[2],
    "workspace": sys.argv[3],
    "servo_revision": sys.argv[4],
    "code_server_addr": sys.argv[5],
    "devtools_port": int(sys.argv[6]),
    "webdriver_port": int(sys.argv[7]),
    "idle_seconds": int(sys.argv[8]),
    "build_mode": sys.argv[9],
    "workbench_url": sys.argv[10],
}
destination.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

printf '\nCaptured:\n  %s\n  %s\n' "${load_screenshot}" "${idle_screenshot}"
printf '\nFirefox console export is an operator step:\n'
printf '  1. Open about:debugging in Firefox.\n'
printf '  2. Add localhost:%s as a network location and connect.\n' "${devtools_port}"
printf '  3. Inspect the code-server workbench and export the console as:\n     %s\n' "${console_export}"

if ((wait_for_console == 0)); then
  printf 'Console wait disabled; run the classifier after exporting the JSON.\n'
  exit 0
fi
[[ -t 0 ]] || die "interactive stdin is required for console export; rerun in a terminal or pass --no-wait-for-console"
read -r -p 'Press Enter after the console JSON has been exported... '
[[ -s "${console_export}" ]] || die "console export is missing or empty: ${console_export}"
console_export_after="$(python3 - "${console_export}" <<'PY'
import pathlib
import sys

stat = pathlib.Path(sys.argv[1]).stat()
print(f"{stat.st_mtime_ns}:{stat.st_size}")
PY
)"
[[ "${console_export_after}" != "${console_export_before}" ]] ||
  die "console export was not updated during this capture: ${console_export}"
python3 "${SCRIPT_DIR}/vscode-ledger-classify.py" \
  --metadata "${metadata_file}" \
  --output "${LEDGER_DIR}/0001-servoshell.md" \
  "${console_export}"
printf 'Ledger capture complete.\n'
