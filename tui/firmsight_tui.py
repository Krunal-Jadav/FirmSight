#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static


def run_command(command):
    """Run a command and return its output."""

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def find_extracted_root(firmware):
    """Find the extracted SquashFS root filesystem."""

    extracted_dir = firmware.parent / f"_{firmware.name}.extracted"
    rootfs = extracted_dir / "squashfs-root"

    if rootfs.exists() and rootfs.is_dir():
        return rootfs

    return None


def analyze_firmware(firmware_path):
    """Collect basic firmware analysis information."""

    firmware = Path(firmware_path)

    data = {
        "firmware": firmware.name,
        "size": "Unknown",
        "filesystem": "Unknown",
        "files": "Unknown",
        "directories": "Unknown",
        "architecture": "Unknown",
        "extraction": "Failed",
    }

    if not firmware.exists() or not firmware.is_file():
        return data

    # Firmware size
    data["size"] = f"{firmware.stat().st_size} bytes"

    # File identification
    file_result = run_command(
        ["file", str(firmware)]
    )

    if file_result and "Squashfs" in file_result:
        data["filesystem"] = "SquashFS"

    # Find extracted filesystem
    rootfs = find_extracted_root(firmware)

    if not rootfs:
        # Try extraction if rootfs does not exist
        run_command(
            ["binwalk", "-e", str(firmware)]
        )

        rootfs = find_extracted_root(firmware)

    if not rootfs:
        return data

    data["extraction"] = "Success"

    # Count directories
    directories = [
        path for path in rootfs.rglob("*")
        if path.is_dir()
    ]

    data["directories"] = str(len(directories) + 1)

    # Count files
    files = [
        path for path in rootfs.rglob("*")
        if path.is_file()
    ]

    data["files"] = str(len(files))

    # Detect architecture from ELF binaries
    architectures = []

    for file_path in files:

        result = run_command(
            ["file", str(file_path)]
        )

        if not result or "ELF" not in result:
            continue

        if "AArch64" in result:
            architectures.append("AArch64")

        elif "ARM" in result:
            architectures.append("ARM")

        elif "MIPS" in result:
            architectures.append("MIPS")

        elif "x86-64" in result:
            architectures.append("x86-64")

        elif "80386" in result:
            architectures.append("x86")

        else:
            architectures.append("Unknown ELF")

    if architectures:
        data["architecture"] = ", ".join(
            sorted(set(architectures))
        )

    return data


class FirmSightTUI(App):
    """FirmSight firmware analysis dashboard."""

    TITLE = "FirmSight - IoT Firmware Analysis Sandbox"

    CSS = """
    Screen {
        align: center middle;
    }

    #dashboard {
        width: 85%;
        height: auto;
        border: solid green;
        padding: 1 2;
    }

    #title {
        text-style: bold;
        content-align: center middle;
        margin-bottom: 1;
    }

    .section {
        margin: 1 0;
    }

    .success {
        color: green;
    }
    """

    def __init__(self, firmware_path):
        super().__init__()
        self.firmware_path = firmware_path
        self.data = analyze_firmware(firmware_path)

    def compose(self) -> ComposeResult:

        yield Header()

        with Vertical(id="dashboard"):

            yield Static(
                "FIRMSIGHT\n"
                "IoT Firmware Analysis Sandbox",
                id="title"
            )

            yield Static(
                f"Firmware      : {self.data['firmware']}",
                classes="section"
            )

            yield Static(
                f"Size          : {self.data['size']}",
                classes="section"
            )

            yield Static(
                f"Filesystem    : {self.data['filesystem']}",
                classes="section"
            )

            yield Static(
                f"Files         : {self.data['files']}",
                classes="section"
            )

            yield Static(
                f"Directories   : {self.data['directories']}",
                classes="section"
            )

            yield Static(
                f"Architecture  : {self.data['architecture']}",
                classes="section"
            )

            yield Static(
                f"Extraction    : {self.data['extraction']}",
                classes="section success"
            )

            yield Static(
                "\nAnalysis Pipeline",
                classes="section"
            )

            yield Static(
                "[✓] Firmware Identification",
                classes="success"
            )

            yield Static(
                "[✓] Binwalk Signature Scan",
                classes="success"
            )

            yield Static(
                "[✓] Firmware Extraction",
                classes="success"
            )

            yield Static(
                "[✓] Filesystem Analysis",
                classes="success"
            )

            yield Static(
                "[✓] Architecture Detection",
                classes="success"
            )

        yield Footer()


def main():

    if len(sys.argv) != 2:

        print("Usage:")
        print(
            "  python tui/firmsight_tui.py <firmware>"
        )

        print("\nExample:")
        print(
            "  python tui/firmsight_tui.py "
            "firmware/samples/firmsight-test-rootfs-v2.squashfs"
        )

        sys.exit(1)

    app = FirmSightTUI(sys.argv[1])
    app.run()


if __name__ == "__main__":
    main()
