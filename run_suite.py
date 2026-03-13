"""
run_suite.py
------------
Auto-discovers and runs ALL scenario*.py files found in the scenarios/
folder, then produces:
  - One individual HTML report per scenario  → reports/result/<name>_<ts>.html
  - One combined suite HTML report           → reports/result/suite_<ts>.html

Adding a new scenario requires NO changes here.
Just create scenarios/scenarioN.py with:
  - A top-level SCENARIO_META dict  (name, description, suite_name)
  - An async main() function

Usage:
    python run_suite.py

The suite report is opened automatically in the default browser when done.
"""

import asyncio
import glob
import importlib.util
import os
import sys
import webbrowser
from datetime import datetime, timedelta

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from libs.config_reader import ConfigReader
from libs.report_manager import SUITE_NAME
from libs.reporter import SuiteReporter

# ---------------------------------------------------------------------------
# Load ALL config keys once for the entire suite run
# ---------------------------------------------------------------------------
ConfigReader.load_to_environ([
    "OPENAI_API_KEY",
    "JIRA_URL", "JIRA_USERNAME", "JIRA_API_TOKEN", "JIRA_PROJECTS_FILTER",
    "BROWSER_URL", "BROWSER_USERNAME", "BROWSER_PASSWORD",
    "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE",
    "REST_BASE_URL", "FILESYSTEM_PATH",
])

SCENARIOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenarios")


# ---------------------------------------------------------------------------
# Lightweight result object consumed by SuiteReporter.add()
# ---------------------------------------------------------------------------

class _ScenarioResult:
    """
    Minimal structure compatible with SuiteReporter.add().
    Built from the SCENARIO_META dict of each discovered module + timing.
    """

    def __init__(self, meta: dict, passed: bool, duration_seconds: float, error_message: str = ""):
        self.scenario_name  = meta.get("name", "Unknown Scenario")
        self.description    = meta.get("description", "")
        self.suite_name     = meta.get("suite_name", SUITE_NAME)
        self._status        = "PASS" if passed else "FAIL"
        self._steps         = []
        self._error_message = error_message
        self._end_time      = datetime.now()
        self._start_time    = self._end_time - timedelta(seconds=duration_seconds)

    def _duration_str(self) -> str:
        return f"{(self._end_time - self._start_time).total_seconds():.1f}s"


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _discover_scenarios() -> list[tuple[str, object]]:
    """
    Glob scenarios/scenario*.py in alphabetical order.
    Returns a list of (file_path, module) tuples for every file that:
      - matches the pattern
      - is NOT __init__.py
      - exposes an async main() function
    """
    pattern = os.path.join(SCENARIOS_DIR, "scenario*.py")
    files   = sorted(glob.glob(pattern))

    discovered = []
    for filepath in files:
        module_name = f"scenarios.{os.path.splitext(os.path.basename(filepath))[0]}"
        spec   = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            print(f"[Suite] ⚠  Could not import {filepath}: {exc}")
            continue

        if not asyncio.iscoroutinefunction(getattr(module, "main", None)):
            print(f"[Suite] ⚠  Skipping {filepath} — no async main() found.")
            continue

        discovered.append((filepath, module))

    return discovered


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    suite    = SuiteReporter(suite_name=SUITE_NAME)
    scenarios = _discover_scenarios()

    if not scenarios:
        print("[Suite] No scenario files discovered. Exiting.")
        return

    print("\n" + "=" * 60)
    print(f"  {SUITE_NAME}")
    print(f"  Discovered {len(scenarios)} scenario(s)")
    print("=" * 60)

    for filepath, module in scenarios:
        filename = os.path.basename(filepath)
        meta     = getattr(module, "SCENARIO_META", {
            "name":        filename,
            "description": "",
            "suite_name":  SUITE_NAME,
        })

        print(f"\n[Suite] ▶  Running: {meta['name']}  ({filename})")

        passed        = False
        error_message = ""
        started       = asyncio.get_event_loop().time()

        try:
            await module.main()  # type: ignore[attr-defined]
            passed = True          # main() raises on failure (re_raise=True default)
        except Exception as exc:
            error_message = str(exc)
            print(f"[Suite] ❌  {meta['name']} raised: {error_message}")
        finally:
            elapsed = asyncio.get_event_loop().time() - started
            suite.add(_ScenarioResult(meta, passed, elapsed, error_message))

    suite_path = suite.save_report()
    webbrowser.open(f"file:///{suite_path.replace(os.sep, '/')}")
    print(f"\n[Suite] 📊 Suite report → {suite_path}")


if __name__ == "__main__":
    asyncio.run(main())

## Run Examples
# python run_suite.py --list
# python run_suite.py --run scenario1,scenario3
# python run_suite.py --skip scenario2
# python run_suite.py --run scenario --skip scenario3 --no-open
