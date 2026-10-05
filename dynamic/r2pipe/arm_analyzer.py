#!/usr/bin/env python3

import sys
import r2pipe


def analyze_binary(binary_path):
    print("=" * 60)
    print("        FirmSight r2pipe ARM Analyzer")
    print("=" * 60)

    print(f"\n[+] Binary: {binary_path}")

    r2 = r2pipe.open(binary_path)

    try:
        r2.cmd("e bin.relocs.apply=true")
        r2.cmd("aaa")

        info = r2.cmdj("ij")

        if info:
            binary_info = info.get("bin", {})

            print("\n[1] Binary Information")
            print("-" * 60)
            print(f"Architecture : {binary_info.get('arch', 'Unknown')}")
            print(f"Bits         : {binary_info.get('bits', 'Unknown')}")
            print(f"Format       : {binary_info.get('bintype', 'Unknown')}")
            print(f"Machine      : {binary_info.get('machine', 'Unknown')}")

        functions = r2.cmdj("aflj") or []

        print("\n[2] Functions")
        print("-" * 60)

        for function in functions:
            print(
                f"{function.get('name', 'unknown')}"
                f" @ {function.get('offset', 0):#x}"
            )

        strings = r2.cmdj("izzj") or []

        print("\n[3] Strings")
        print("-" * 60)

        for string in strings:
            value = string.get("string")

            if value:
                print(value)

    finally:
        r2.quit()

    print("\n[+] Analysis completed.")


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python3 dynamic/r2pipe/arm_analyzer.py <ARM-ELF>")
        sys.exit(1)

    analyze_binary(sys.argv[1])


if __name__ == "__main__":
    main()
