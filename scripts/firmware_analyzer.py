#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path


def run_command(command):
    """Run a system command and return its output."""

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"[!] Command failed: {' '.join(command)}")

        if result.stderr:
            print(result.stderr.strip())

        return None

    return result.stdout


def find_extracted_root(firmware):
    """Find the SquashFS extraction directory created by Binwalk."""

    extracted_dir = firmware.parent / f"_{firmware.name}.extracted"
    rootfs = extracted_dir / "squashfs-root"

    if rootfs.exists() and rootfs.is_dir():
        return rootfs

    return None


def detect_architectures(rootfs):
    """Detect architectures from ELF binaries in the extracted filesystem."""

    print("\n[5] Architecture Detection")
    print("-" * 60)

    detected = []

    for file_path in rootfs.rglob("*"):

        if not file_path.is_file():
            continue

        result = run_command(["file", str(file_path)])

        if not result:
            continue

        output = result.strip()

        # Only treat ELF files as executable architecture evidence.
        if "ELF" not in output:
            continue

        print(f"[+] Binary: {file_path}")
        print(f"    {output}")

        if "AArch64" in output:
            architecture = "AArch64"
        elif "ARM" in output:
            architecture = "ARM"
        elif "MIPS" in output:
            architecture = "MIPS"
        elif "x86-64" in output:
            architecture = "x86-64"
        elif "80386" in output or "Intel 80386" in output:
            architecture = "x86"
        else:
            architecture = "Unknown ELF architecture"

        detected.append(architecture)

    if detected:
        print("\n[+] Detected Architectures:")

        for architecture in sorted(set(detected)):
            print(f"    - {architecture}")

    else:
        print("[!] No ELF binaries found.")


def analyze_filesystem(rootfs):
    """Analyze files and directories inside extracted firmware."""

    print("\n[4] Filesystem Analysis")
    print("-" * 60)

    directories = [
        path for path in rootfs.rglob("*")
        if path.is_dir()
    ]

    files = [
        path for path in rootfs.rglob("*")
        if path.is_file()
    ]

    print(f"[+] Root filesystem: {rootfs}")
    print(f"[+] Directories: {len(directories) + 1}")
    print(f"[+] Files: {len(files)}")

    print("\n[+] File Types")
    print("-" * 60)

    for file_path in files:

        result = run_command(
            ["file", str(file_path)]
        )

        if result:
            print(result.strip())

    detect_architectures(rootfs)


def analyze_firmware(firmware_path):
    """Identify, scan, extract, and analyze firmware."""

    firmware = Path(firmware_path)

    if not firmware.exists():
        print(f"[!] Firmware not found: {firmware}")
        return

    if not firmware.is_file():
        print(f"[!] Path is not a file: {firmware}")
        return

    print("=" * 60)
    print("        FirmSight Firmware Analyzer")
    print("=" * 60)

    print(f"\n[+] Firmware: {firmware}")
    print(f"[+] Size: {firmware.stat().st_size} bytes")

    # ---------------------------------------------------------
    # 1. File Identification
    # ---------------------------------------------------------

    print("\n[1] File Identification")
    print("-" * 60)

    file_result = run_command(
        ["file", str(firmware)]
    )

    if file_result:
        print(file_result.strip())

    # ---------------------------------------------------------
    # 2. Binwalk Signature Scan
    # ---------------------------------------------------------

    print("\n[2] Binwalk Signature Scan")
    print("-" * 60)

    binwalk_result = run_command(
        ["binwalk", "-B", str(firmware)]
    )

    if binwalk_result:
        print(binwalk_result.strip())

    # ---------------------------------------------------------
    # 3. Firmware Extraction
    # ---------------------------------------------------------

    print("\n[3] Firmware Extraction")
    print("-" * 60)

    extraction_result = run_command(
        ["binwalk", "-e", str(firmware)]
    )

    if extraction_result:
        print(extraction_result.strip())

    # ---------------------------------------------------------
    # Find extracted filesystem
    # ---------------------------------------------------------

    rootfs = find_extracted_root(firmware)

    if rootfs:
        analyze_filesystem(rootfs)
    else:
        print("\n[!] Extracted SquashFS root filesystem not found.")

    print("\n[+] Analysis completed.")


def main():
    """Program entry point."""

    if len(sys.argv) != 2:

        print("Usage:")
        print(
            "  python3 scripts/firmware_analyzer.py <firmware>"
        )

        sys.exit(1)

    analyze_firmware(sys.argv[1])


if __name__ == "__main__":
    main()
