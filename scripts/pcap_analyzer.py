
#!/usr/bin/env python3

import json
import sys
from collections import Counter
from pathlib import Path

from scapy.all import PcapReader, IP, IPv6, TCP, UDP, DNS

SUSPICIOUS_PORTS = {23, 2323, 4444, 5555}


def analyze_pcap(path):
    file_path = Path(path)

    if not file_path.is_file():
        return {"error": f"PCAP file not found: {file_path}"}

    protocols = Counter()
    hosts = set()
    total = 0
    tcp_syn = 0
    dns_queries = 0
    indicators = []

    try:
        with PcapReader(str(file_path)) as packets:
            for packet in packets:
                total += 1

                if IP in packet:
                    src, dst = packet[IP].src, packet[IP].dst
                elif IPv6 in packet:
                    src, dst = packet[IPv6].src, packet[IPv6].dst
                else:
                    protocols["Other"] += 1
                    continue

                hosts.add(src)
                hosts.add(dst)
                protocols["IP"] += 1

                if TCP in packet:
                    protocols["TCP"] += 1
                    tcp = packet[TCP]

                    if tcp.flags & 0x02 and not tcp.flags & 0x10:
                        tcp_syn += 1

                    for port in {tcp.sport, tcp.dport} & SUSPICIOUS_PORTS:
                        indicators.append(
                            f"Review port {port}: {src} -> {dst}"
                        )

                elif UDP in packet:
                    protocols["UDP"] += 1

                    if DNS in packet and packet[DNS].qd:
                        dns_queries += 1
    except Exception as exc:
        return {"error": f"Could not read PCAP: {exc}"}

    return {
        "file": file_path.name,
        "total_packets": total,
        "protocols": dict(protocols),
        "unique_hosts": len(hosts),
        "tcp_syn": tcp_syn,
        "dns_queries": dns_queries,
        "indicators": sorted(set(indicators)),
    }


def main():
    if len(sys.argv) not in (2, 3):
        print(
            f"Usage: {sys.argv[0]} <capture.pcap> [--json]",
            file=sys.stderr,
        )
        return 2

    result = analyze_pcap(sys.argv[1])

    if len(sys.argv) == 3 and sys.argv[2] == "--json":
        print(json.dumps(result))
    elif "error" in result:
        print(f"[-] {result['error']}")
        return 1
    else:
        print(f"\nFirmSight PCAP Analysis: {result['file']}\n")
        print(f"Total packets: {result['total_packets']}")
        print(f"Protocol counts: {result['protocols']}")
        print(f"Unique hosts: {result['unique_hosts']}")
        print(f"TCP SYN packets: {result['tcp_syn']}")
        print(f"DNS queries: {result['dns_queries']}")

        for indicator in result["indicators"]:
            print(f"[!] {indicator}")

        print("\n[+] Analysis completed.")

    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
