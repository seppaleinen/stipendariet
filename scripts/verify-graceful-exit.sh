#!/usr/bin/env bash
# verify-graceful-exit.sh — verify a Python script's graceful-exit path when optional deps are missing.
#
# Usage:
#   verify-graceful-exit.sh <expected-exit> <expected-stdout-substring> <module:function> [blocklist]
#   verify-graceful-exit.sh <expected-exit> <expected-stdout-substring> -- <python-script.py> [blocklist]
#
# Examples:
#   verify-graceful-exit.sh 0 "sqlalchemy/dbapi unavailable" migrations_check:main "psycopg2,psycopg"
#   verify-graceful-exit.sh 0 "skipping check" -- ./migrations_check.py
#
# The script runs the target with the specified imports blocked via a sys.meta_path finder,
# capturing stdout/stderr/exit. It asserts:
#   - exit code == expected-exit
#   - expected-stdout-substring appears on stdout
#   - NO traceback appears on stdout or stderr
#
# Exit codes: 0=pass, 1=fail (mismatch), 2=usage error.

set -euo pipefail

if [[ $# -lt 3 ]]; then
    cat <<'EOF' >&2
Usage:
  verify-graceful-exit.sh <expected-exit> <expected-stdout-substring> <module:function> [blocklist]
  verify-graceful-exit.sh <expected-exit> <expected-stdout-substring> -- <script.py> [blocklist]

Arguments:
  expected-exit          Numeric exit code the target should return (e.g., 0)
  expected-stdout-substring  Text that MUST appear on stdout (not stderr)
  module:function        Import module, call function (e.g., migrations_check:main)
  -- script.py           Run script as __main__ (blocker applies in-process)
  blocklist              Comma-separated top-level modules to block (default: psycopg2,psycopg,psycopg2-binary,psycopg2_binary)
EOF
    exit 2
fi

EXPECTED_EXIT=$1
EXPECTED_SUBSTR=$2
shift 2

if [[ "$1" == "--" ]]; then
    # Script mode
    shift
    TARGET=$1
    BLOCKLIST="${2:-psycopg2,psycopg,psycopg2-binary,psycopg2_binary}"
    MODE="script"
else
    # Module:function mode
    TARGET=$1
    BLOCKLIST="${2:-psycopg2,psycopg,psycopg2-binary,psycopg2_binary}"
    MODE="module"
fi

# Run the in-process blocker; results written to a temp file for robust parsing
RESULTS=$(mktemp)
export BLOCKLIST MODE TARGET EXPECTED_EXIT EXPECTED_SUBSTR RESULTS
python3 <<'PYEOF'
import sys
import io
import contextlib
import os

blocklist = set(os.environ.get("BLOCKLIST", "").split(","))
blocklist = {b.strip() for b in blocklist if b.strip()}

class _Blocker:
    def find_spec(self, fullname, path, target=None):
        top_level = fullname.split(".")[0]
        if top_level in blocklist:
            raise ModuleNotFoundError(f"Blocked import for testing: {fullname}")
        return None

sys.meta_path.insert(0, _Blocker())

# Purge already-cached blocked modules
for name in list(sys.modules.keys()):
    top_level = name.split(".")[0]
    if top_level in blocklist:
        del sys.modules[name]

mode = os.environ["MODE"]
target = os.environ["TARGET"]
expected_exit = int(os.environ["EXPECTED_EXIT"])
expected_substr = os.environ["EXPECTED_SUBSTR"]
results_path = os.environ["RESULTS"]

stdout_buf = io.StringIO()
stderr_buf = io.StringIO()
actual_exit = 0
traceback_found = False

try:
    if mode == "module":
        mod_name, func_name = target.split(":", 1)
        mod = __import__(mod_name, fromlist=[func_name])
        func = getattr(mod, func_name)
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            result = func()
            if result is not None:
                actual_exit = result
    else:  # script mode
        with open(target, "r") as f:
            code = compile(f.read(), target, 'exec')
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            exec(code, {"__name__": "__main__", "__file__": target})
except SystemExit as e:
    actual_exit = e.code if isinstance(e.code, int) else 1
except Exception:
    import traceback
    traceback.print_exc(file=stderr_buf)
    traceback_found = True
    actual_exit = 1

stdout = stdout_buf.getvalue()
stderr = stderr_buf.getvalue()

if "Traceback" in stdout or "Traceback" in stderr:
    traceback_found = True

# Write results to file with simple KEY=VALUE format (no newlines in values)
with open(results_path, "w") as f:
    f.write(f"EXIT={actual_exit}\n")
    f.write(f"TRACEBACK={1 if traceback_found else 0}\n")
    # Escape newlines in stdout/stderr
    f.write(f"STDOUT={stdout.replace(chr(10), '\\n')}\n")
    f.write(f"STDERR={stderr.replace(chr(10), '\\n')}\n")
PYEOF

# Read results
ACTUAL_EXIT=$(grep '^EXIT=' "$RESULTS" | cut -d= -f2)
TRACEBACK=$(grep '^TRACEBACK=' "$RESULTS" | cut -d= -f2)
STDOUT_ESCAPED=$(grep '^STDOUT=' "$RESULTS" | cut -d= -f2-)
STDERR_ESCAPED=$(grep '^STDERR=' "$RESULTS" | cut -d= -f2-)
rm -f "$RESULTS"

# Unescape newlines
ACTUAL_STDOUT=$(printf '%b' "$STDOUT_ESCAPED")
ACTUAL_STDERR=$(printf '%b' "$STDERR_ESCAPED")

# Check conditions
FAIL=0
if [[ "$ACTUAL_EXIT" != "$EXPECTED_EXIT" ]]; then
    echo "FAIL: exit code $ACTUAL_EXIT != expected $EXPECTED_EXIT" >&2
    FAIL=1
fi
if [[ "$ACTUAL_STDOUT" != *"$EXPECTED_SUBSTR"* ]]; then
    echo "FAIL: expected substring '$EXPECTED_SUBSTR' not found in stdout:" >&2
    echo "  stdout: $ACTUAL_STDOUT" >&2
    FAIL=1
fi
if [[ "$TRACEBACK" == "1" ]]; then
    echo "FAIL: traceback found in output" >&2
    echo "  stderr: $ACTUAL_STDERR" >&2
    FAIL=1
fi

if [[ $FAIL -eq 0 ]]; then
    echo "PASS: graceful exit verified (exit=$ACTUAL_EXIT, substring found, no traceback)"
    exit 0
else
    exit 1
fi