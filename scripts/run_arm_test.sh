#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$PROJECT_DIR/tests/fixtures/firmsight-arm-test.c"
BUILD_DIR="$PROJECT_DIR/build"
BINARY="$BUILD_DIR/firmsight-arm-test"
SYSROOT="/usr/arm-linux-gnueabihf"
LOADER="$SYSROOT/lib/ld-linux-armhf.so.3"

echo "=============================================="
echo "       FirmSight ARM QEMU Test"
echo "=============================================="

if ! command -v arm-linux-gnueabihf-gcc >/dev/null 2>&1; then
    echo "[!] ARM cross-compiler is missing."
    echo "Install it with: sudo apt install gcc-arm-linux-gnueabihf"
    exit 1
fi

if ! command -v qemu-arm >/dev/null 2>&1; then
    echo "[!] QEMU user-mode is missing."
    echo "Install it with: sudo apt install qemu-user"
    exit 1
fi

if [[ ! -f "$SOURCE" ]]; then
    echo "[!] ARM test source not found: $SOURCE"
    exit 1
fi

if [[ ! -x "$LOADER" ]]; then
    echo "[!] ARMHF loader not found: $LOADER"
    echo "Check the ARM cross-compiler runtime/sysroot installation."
    exit 1
fi

mkdir -p "$BUILD_DIR"

echo
echo "[1] Compiling ARM test program..."
arm-linux-gnueabihf-gcc "$SOURCE" -o "$BINARY"

echo
echo "[2] Checking binary architecture..."
file "$BINARY"

echo
echo "[3] Executing with QEMU ARM..."
qemu-arm -L "$SYSROOT" "$BINARY"

echo
echo "[+] PASS: ARM program compiled and executed successfully."
