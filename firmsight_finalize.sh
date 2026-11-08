#!/usr/bin/env bash
set -u

PROJECT="$HOME/FirmSight"
cd "$PROJECT" || exit 1

echo "=========================================="
echo "       FIRMSIGHT FINAL SUBMISSION"
echo "=========================================="

BRANCH=$(git branch --show-current 2>/dev/null || true)

if [[ "$BRANCH" != "Krunal-Jadav" ]]; then
    echo "[ERROR] Expected branch Krunal-Jadav."
    echo "[ERROR] Current branch: $BRANCH"
    exit 1
fi

mkdir -p logs tests/fixtures

echo
echo "[1/7] Checking dependencies..."

if ! command -v strace >/dev/null 2>&1; then
    echo "[WARN] strace missing. Install: sudo apt install strace"
fi

if [[ -x ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

echo "Using Python: $PYTHON"

echo
echo "[2/7] Creating runtime tracing script..."

cat > scripts/runtime_tracer.py <<'PY'
#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="FirmSight runtime system-call tracer"
    )
    parser.add_argument("--output", default="logs/runtime_trace.log")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = args.command
    if command and command[0] == "--":
        command = command[1:]

    if not command:
        parser.error("Provide a command after --")

    tracer = shutil.which("strace")
    if not tracer:
        print("[ERROR] Install strace first.")
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    trace = [
        tracer, "-f", "-tt", "-T", "-s", "256",
        "-e", "trace=%process,%network,%file",
        "-o", str(output), "--", *command
    ]

    print("[+] Tracing:", " ".join(command))
    result = subprocess.run(trace, check=False)
    print("[+] Trace saved:", output)
    print("[+] Exit code:", result.returncode)
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
PY

chmod +x scripts/runtime_tracer.py

echo
echo "[3/7] Creating behavioral alert analyzer..."

cat > scripts/behavior_alerts.py <<'PY'
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

SUSPICIOUS_PORTS = {
    23: "Telnet",
    2323: "Alternative Telnet",
    4444: "Potential reverse-shell port",
    5555: "Potential debug/backdoor port",
    6667: "IRC",
    31337: "Suspicious service port",
}

def analyze(data):
    alerts = []

    for packet in data.get("packets", []):
        src = packet.get("src", "")
        dst = packet.get("dst", "")

        for field in ("sport", "dport"):
            try:
                port = int(packet.get(field))
            except (TypeError, ValueError):
                continue

            if port in SUSPICIOUS_PORTS:
                alerts.append({
                    "severity": "HIGH",
                    "type": "SUSPICIOUS_PORT",
                    "port": port,
                    "service": SUSPICIOUS_PORTS[port],
                    "source": src,
                    "destination": dst,
                    "message": f"Traffic involving port {port}"
                })

    return alerts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", default="logs/behavior_alerts.json")
    args = parser.parse_args()

    try:
        data = json.loads(Path(args.input).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    if not isinstance(data, dict) or not isinstance(data.get("packets", []), list):
        parser.error("Expected JSON object containing a packets array")

    alerts = analyze(data)
    result = {"total_alerts": len(alerts), "alerts": alerts}

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2))

    print(f"[+] Behavioral analysis: {len(alerts)} alert(s)")
    print(f"[+] Saved: {output}")

    for alert in alerts:
        print(f"[{alert['severity']}] {alert['message']}")

if __name__ == "__main__":
    main()
PY

chmod +x scripts/behavior_alerts.py

cat > tests/fixtures/behavior-test.json <<'JSON'
{
  "packets": [
    {"src":"192.168.1.10","dst":"192.168.1.20","sport":45000,"dport":4444},
    {"src":"192.168.1.20","dst":"8.8.8.8","sport":53000,"dport":53},
    {"src":"192.168.1.30","dst":"192.168.1.40","sport":23,"dport":50000}
  ]
}
JSON

echo
echo "[4/7] Creating isolated execution helper..."

cat > scripts/run_isolated.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 command [arguments...]"
    exit 1
fi

command -v unshare >/dev/null 2>&1 || {
    echo "[ERROR] util-linux unshare unavailable."
    exit 1
}

echo "[+] Attempting isolated network namespace."
exec unshare --net -- "$@"
SH

chmod +x scripts/run_isolated.sh

echo
echo "[5/7] Running syntax and behavior tests..."

TEST_STATUS=0

"$PYTHON" -m py_compile \
    scripts/runtime_tracer.py \
    scripts/behavior_alerts.py \
    scripts/pcap_analyzer.py \
    scripts/firmware_analyzer.py \
    dynamic/r2pipe/arm_analyzer.py \
    tui/firmsight_tui.py || TEST_STATUS=1

"$PYTHON" scripts/behavior_alerts.py \
    tests/fixtures/behavior-test.json || TEST_STATUS=1

if [[ -f logs/behavior_alerts.json ]]; then
    "$PYTHON" - <<'PY' || TEST_STATUS=1
import json
with open("logs/behavior_alerts.json") as f:
    result = json.load(f)
count = result["total_alerts"]
print(f"[+] Expected 2 alerts; observed {count}")
assert count == 2
PY
fi

echo
echo "[6/7] Testing runtime tracing..."

if command -v strace >/dev/null 2>&1; then
    "$PYTHON" scripts/runtime_tracer.py \
        --output logs/runtime_test.log -- /bin/echo "FirmSight runtime test" \
        || TEST_STATUS=1
else
    echo "[WARN] Runtime tracing not tested: strace unavailable."
    TEST_STATUS=1
fi

echo
echo "[7/7] Testing network isolation..."

if bash scripts/run_isolated.sh /bin/echo "Isolated test"; then
    echo "[PASS] Network namespace test."
else
    echo "[WARN] Network namespace unavailable in this environment."
    echo "[WARN] TUN/TAP and network isolation remain incomplete."
fi

echo
echo "=========================================="
echo "             FINAL SUMMARY"
echo "=========================================="

if [[ "$TEST_STATUS" -eq 0 ]]; then
    echo "[PASS] Implemented-script syntax and alert/runtime tests."
else
    echo "[WARN] One or more tests failed. Inspect output."
fi

echo
echo "Git branch: $(git branch --show-current)"
echo "Git status:"
git status --short

echo
echo "No automatic commit or push was performed."
echo "Review the changes before submission."
