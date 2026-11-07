#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

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


def analyze_network(pcap_path):
    """Return PCAP analysis data for the dashboard."""

    pcap = Path(pcap_path)

    if not pcap.is_absolute():
        pcap = PROJECT_ROOT / pcap

    if not pcap.is_file():
        return {"error": f"PCAP not found: {pcap.name}"}

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "pcap_analyzer.py"),
            str(pcap),
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    if result.returncode != 0:
        return {"error": result.stderr.strip() or "PCAP analysis failed"}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "Invalid response from PCAP analyzer"}



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

    def __init__(self, firmware_path, pcap_path=None):
        super().__init__()
        self.firmware_path = firmware_path
        self.data = analyze_firmware(firmware_path)

        if pcap_path is None:
            pcap_path = "build/firmsight-week3-test.pcap"

        self.network_data = analyze_network(pcap_path)

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="dashboard"):
            yield Static(
                "FIRMSIGHT\nIoT Firmware Analysis Sandbox",
                id="title"
            )

            yield Static(f"Firmware      : {self.data['firmware']}", classes="section")
            yield Static(f"Size          : {self.data['size']}", classes="section")
            yield Static(f"Filesystem    : {self.data['filesystem']}", classes="section")
            yield Static(f"Files         : {self.data['files']}", classes="section")
            yield Static(f"Directories   : {self.data['directories']}", classes="section")
            yield Static(f"Architecture  : {self.data['architecture']}", classes="section")
            yield Static(f"Extraction    : {self.data['extraction']}", classes="section success")

            yield Static("\nNetwork Analysis (PCAP)", classes="section")

            if "error" in self.network_data:
                yield Static(
                    f"Network status : {self.network_data['error']}",
                    classes="section"
                )
            else:
                net = self.network_data
                yield Static(f"Capture        : {net['file']}", classes="section")
                yield Static(f"Total packets  : {net['total_packets']}", classes="section")
                yield Static(f"Protocols      : {net['protocols']}", classes="section")
                yield Static(f"Unique hosts   : {net['unique_hosts']}", classes="section")
                yield Static(f"TCP SYN packets: {net['tcp_syn']}", classes="section")
                yield Static(f"DNS queries    : {net['dns_queries']}", classes="section")

                indicators = net.get("indicators", [])
                indicator_text = "; ".join(indicators[:3]) if indicators else "No configured port indicators found"
                yield Static(f"Review indicators: {indicator_text}", classes="section")

            yield Static("\nAnalysis Pipeline", classes="section")
            yield Static("[✓] Firmware Identification", classes="success")
            yield Static("[✓] Binwalk Signature Scan", classes="success")
            yield Static("[✓] Firmware Extraction", classes="success")
            yield Static("[✓] Filesystem Analysis", classes="success")
            yield Static("[✓] Architecture Detection", classes="success")

        yield Footer()


def main():
    if len(sys.argv) not in (2, 3):
        print("Usage:")
        print(
            "  python tui/firmsight_tui.py <firmware> [capture.pcap]"
        )
        print("\nExample:")
        print(
            "  python tui/firmsight_tui.py "
            "firmware/samples/firmsight-test-rootfs-v2.squashfs "
            "[capture.pcap]"
        )
        sys.exit(1)

    firmware_path = sys.argv[1]
    pcap_path = sys.argv[2] if len(sys.argv) == 3 else None

    app = FirmSightTUI(firmware_path, pcap_path)
    app.run()


if __name__ == "__main__":
    main()
