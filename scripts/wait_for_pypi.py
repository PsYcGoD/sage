"""Wait until PyPI serves the Python core required by the npm launcher."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--interval", type=int, default=10)
    args = parser.parse_args()

    expected = args.version.removeprefix("v")
    deadline = time.monotonic() + max(1, args.timeout)
    url = "https://pypi.org/pypi/psycgod-sage/json"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}?t={time.time_ns()}", timeout=15) as response:
                current = str(json.load(response)["info"]["version"])
            if current == expected:
                print(f"PyPI core is ready: {current}")
                return 0
            print(f"PyPI currently serves {current}; waiting for {expected}")
        except Exception as exc:
            print(f"PyPI check failed temporarily: {exc}")
        time.sleep(max(1, args.interval))

    print(f"Timed out waiting for psycgod-sage {expected} on PyPI", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
