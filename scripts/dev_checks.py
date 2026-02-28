from __future__ import annotations

import subprocess
import sys


COMMANDS = [
    [sys.executable, "scripts/validate_plugin_specs.py"],
    [sys.executable, "-m", "pytest", "tests/test_plugin_sdk.py", "tests/test_schema_validation_service.py", "tests/test_simulation_service.py"],
]


def main() -> int:
    for cmd in COMMANDS:
        print(f"> {' '.join(cmd)}")
        completed = subprocess.run(cmd)
        if completed.returncode != 0:
            return completed.returncode
    print("Developer fast checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
