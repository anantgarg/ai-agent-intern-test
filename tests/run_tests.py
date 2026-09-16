from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))


def main() -> int:
    failures: list[str] = []
    for module_name in ("test_orders", "test_agent"):
        module = importlib.import_module(module_name)
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            try:
                func()
                print(f"PASS {module_name}.{name}")
            except Exception as exc:  # noqa: BLE001 - test runner should report every assertion failure.
                print(f"FAIL {module_name}.{name}: {exc}")
                failures.append(f"{module_name}.{name}")
    print(f"\nOverall: {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

