
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scapy.all import Ether, IP, TCP, wrpcap

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYZER = PROJECT_ROOT / "scripts" / "pcap_analyzer.py"


class TestPcapAnalyzer(unittest.TestCase):
    def test_analyzes_tcp_packet(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pcap_path = Path(temp_dir) / "test.pcap"

            packet = (
                Ether()
                / IP(src="192.0.2.10", dst="192.0.2.20")
                / TCP(sport=45678, dport=2323, flags="S")
            )
            wrpcap(str(pcap_path), [packet])

            result = subprocess.run(
                [sys.executable, str(ANALYZER), str(pcap_path)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Total packets: 1", result.stdout)
            self.assertIn("TCP SYN packets: 1", result.stdout)
            self.assertIn("Review port 2323", result.stdout)
            self.assertIn("Analysis completed", result.stdout)

    def test_missing_file_returns_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.pcap"

            result = subprocess.run(
                [sys.executable, str(ANALYZER), str(missing_path)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("PCAP file not found", result.stdout)


if __name__ == "__main__":
    unittest.main()

