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
