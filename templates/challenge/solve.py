#!/usr/bin/env python3
"""Internal acceptance solver. Print the recovered flag and return 0 on success.

Set SOLVE_TARGET for a deployed instance. The default targets the local compose port.
Do not place a production flag in this source file.
"""

import os
import sys


def main() -> int:
    target = os.environ.get("SOLVE_TARGET", "http://127.0.0.1:18080")
    print(f"Implement the solver for {target}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
