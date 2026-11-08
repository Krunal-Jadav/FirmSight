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
