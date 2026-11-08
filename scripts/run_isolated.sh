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
