"""
report_manager.py
-----------------
Centralised helper that manages the full ScenarioReporter lifecycle
for any scenario team run.

Every scenario (and the suite runner) delegates to this single function,
eliminating repetitive try/except/finally reporter boilerplate.

Usage
-----
from libs.report_manager import run_scenario_with_report

result = await run_scenario_with_report(
    team=team,
    model_client=model_client,
    scenario_name="Scenario 4 - MySQL Department Data Query",
    description="Verifies bakery_hr departments.",
    task="Get department data ...",
    pass_condition_text="DEPARTMENT_DATA_READY",
    suite_name="AgenticAI Test Suite",   # optional
    re_raise=True,                        # optional, default True
)

# result is a dict:
# {
#   "passed":        bool,
#   "report_path":   str,   absolute path to generated HTML
#   "error_message": str,   empty string when no error
# }
"""

from typing import Optional
from libs.reporter import ScenarioReporter

# ---------------------------------------------------------------------------
# Single source of truth for the suite name.
# Import this constant in run_suite.py and scenario files instead of
# repeating the string literal everywhere.
# ---------------------------------------------------------------------------
SUITE_NAME = "AgenticAI Test Suite"


async def run_scenario_with_report(
    *,
    team,
    model_client,
    scenario_name: str,
    description: str = "",
    task: str,
    pass_condition_text: str,
    suite_name: str = SUITE_NAME,
    re_raise: bool = True,
) -> dict:
    """
    Run a scenario team with a fully managed ScenarioReporter lifecycle.

    Handles:
      - reporter.start()
      - team.run_stream() capture via reporter.run_and_collect()
      - pass/fail determination from termination keyword
      - reporter.finish() and reporter.save_report() called exactly once
      - model_client.close() always called in finally
      - optional re-raise of any exception after reporting

    Parameters
    ----------
    team              : RoundRobinGroupChat (or any AutoGen team)
    model_client      : OpenAIChatCompletionClient
    scenario_name     : Human-readable name shown in the report header
    description       : Short description of what the scenario tests
    task              : The task string passed to team.run_stream()
    pass_condition_text : Keyword that indicates a PASS when found in any message
    suite_name        : Groups this scenario in the suite report
    re_raise          : If True (default), re-raises any caught exception after saving the report.
                        Set to False when running inside run_suite.py so one failure
                        does not abort the remaining scenarios.

    Returns
    -------
    dict with keys:
        passed        (bool)  – True if pass_condition_text was found
        report_path   (str)   – Absolute path to the saved HTML report
        error_message (str)   – Empty string on success, exception text on failure
    """
    reporter = ScenarioReporter(
        scenario_name=scenario_name,
        description=description,
        suite_name=suite_name,
    )

    reporter.start()
    passed = False
    error_message = ""
    caught_exception: Optional[Exception] = None

    try:
        task_result = await reporter.run_and_collect(team, task=task)
        passed = any(
            pass_condition_text in str(getattr(m, "content", ""))
            for m in task_result.messages
        )
    except Exception as exc:
        caught_exception = exc
        error_message = str(exc)
    finally:
        reporter.finish(passed=passed, error_message=error_message)
        report_path = reporter.save_report()
        await model_client.close()

    if caught_exception and re_raise:
        raise caught_exception

    return {
        "passed": passed,
        "report_path": report_path,
        "error_message": error_message,
    }

