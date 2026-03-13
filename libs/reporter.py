"""
reporter.py
-----------
Captures agent conversation messages during scenario runs and generates
rich HTML test reports saved to AgenticAIAutoGen/reports/result/.

Usage (inside a scenario)
--------------------------
from libs.reporter import ScenarioReporter

reporter = ScenarioReporter(scenario_name="Scenario 1 – Jira Bug Analysis + Playwright")
reporter.start()

# Wrap team.run_stream with the reporter's collector
task_result = await reporter.run_and_collect(team, task="...")

reporter.finish(passed=True)   # or passed=False
reporter.save_report()         # writes reports/result/<scenario>_<timestamp>.html
"""

import os
import re
import html as html_lib
from datetime import datetime
from typing import Optional

from autogen_agentchat.base import TaskResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports', 'result')

_STATUS_COLORS = {
    "PASS": "#28a745",
    "FAIL": "#dc3545",
    "RUNNING": "#fd7e14",
    "SKIPPED": "#6c757d",
}

_AGENT_COLORS = {
    "BugAnalyst":       "#4e79a7",
    "AutomationAgent":  "#f28e2b",
    "DatabaseAgent":    "#59a14f",
    "APIAgent":         "#e15759",
    "ExcelAgent":       "#76b7b2",
    "user":             "#b07aa1",
    "TaskResult":       "#9c755f",
}

_DEFAULT_AGENT_COLOR = "#aaaaaa"


def _agent_color(name: str) -> str:
    return _AGENT_COLORS.get(name, _DEFAULT_AGENT_COLOR)


def _safe_filename(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', text)


# ---------------------------------------------------------------------------
# Message container
# ---------------------------------------------------------------------------

class StepRecord:
    """Represents a single agent message captured during the run."""

    def __init__(self, agent: str, content: str, timestamp: datetime):
        self.agent = agent
        self.content = content
        self.timestamp = timestamp
        self.elapsed_seconds: Optional[float] = None  # filled in later


# ---------------------------------------------------------------------------
# ScenarioReporter
# ---------------------------------------------------------------------------

class ScenarioReporter:
    """
    Captures the execution of one scenario and writes an HTML report.

    Parameters
    ----------
    scenario_name : str
        Human-readable name shown in the report header.
    description : str, optional
        A short description of what the scenario tests.
    suite_name : str, optional
        Groups this scenario under a suite (shown in the suite summary).
    """

    def __init__(
        self,
        scenario_name: str,
        description: str = "",
        suite_name: str = "AgenticAI Test Suite",
    ):
        self.scenario_name = scenario_name
        self.description = description
        self.suite_name = suite_name

        self._steps: list[StepRecord] = []
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._status: str = "RUNNING"
        self._error_message: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Call before running the team."""
        self._start_time = datetime.now()
        self._status = "RUNNING"
        print(f"\n[Reporter] ▶ Starting: {self.scenario_name}")

    def finish(self, passed: bool, error_message: str = ""):
        """Call after the team finishes."""
        self._end_time = datetime.now()
        self._status = "PASS" if passed else "FAIL"
        self._error_message = error_message
        # Back-fill elapsed seconds per step
        for step in self._steps:
            step.elapsed_seconds = (step.timestamp - self._start_time).total_seconds()
        icon = "✅" if passed else "❌"
        print(f"[Reporter] {icon} Finished: {self.scenario_name} — {self._status}")

    # ------------------------------------------------------------------
    # Running
    # ------------------------------------------------------------------

    async def run_and_collect(self, team, task: str) -> TaskResult:
        """
        Runs ``team.run_stream(task=task)``, pipes it through Console for
        live output, and captures every message for the report.

        Returns the TaskResult so callers can inspect messages if needed.
        """
        collected_messages = []
        task_result: Optional[TaskResult] = None

        async for message in team.run_stream(task=task):
            if isinstance(message, TaskResult):
                task_result = message
                self._record_step("TaskResult", f"Task finished. Stop reason: {message.stop_reason}")
            else:
                agent_name = getattr(message, "source", "unknown")
                content = getattr(message, "content", str(message))
                if isinstance(content, list):
                    # MultiModal content → join text parts
                    content = "\n".join(
                        part.text if hasattr(part, "text") else str(part)
                        for part in content
                    )
                self._record_step(str(agent_name), str(content))
                collected_messages.append(message)

        # Return the TaskResult, falling back to a constructed one if needed
        if task_result is not None:
            return task_result
        return TaskResult(messages=collected_messages, stop_reason="unknown")

    def _record_step(self, agent: str, content: str):
        self._steps.append(StepRecord(agent=agent, content=content, timestamp=datetime.now()))

    # ------------------------------------------------------------------
    # reports generation
    # ------------------------------------------------------------------

    def save_report(self) -> str:
        """
        Writes the HTML report to reports/result/<safe_name>_<timestamp>.html.
        Returns the absolute path to the created file.
        """
        os.makedirs(_REPORT_DIR, exist_ok=True)
        ts = (self._start_time or datetime.now()).strftime("%Y%m%d_%H%M%S")
        filename = f"{_safe_filename(self.scenario_name)}_{ts}.html"
        filepath = os.path.abspath(os.path.join(_REPORT_DIR, filename))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self._render_html())

        print(f"[Reporter] 📄 reports saved → {filepath}")
        return filepath

    # ------------------------------------------------------------------
    # HTML rendering
    # ------------------------------------------------------------------

    def _duration_str(self) -> str:
        if self._start_time and self._end_time:
            secs = (self._end_time - self._start_time).total_seconds()
            return f"{secs:.1f}s"
        return "—"

    def _render_html(self) -> str:
        status_color = _STATUS_COLORS.get(self._status, "#6c757d")
        steps_html = "\n".join(self._render_step(i, s) for i, s in enumerate(self._steps))
        error_block = (
            f'<div class="error-block"><strong>⚠ Error:</strong> {html_lib.escape(self._error_message)}</div>'
            if self._error_message else ""
        )

        agent_legend = "\n".join(
            f'<span class="legend-item" style="border-left:4px solid {_agent_color(a)}">{html_lib.escape(a)}</span>'
            for a in dict.fromkeys(s.agent for s in self._steps)
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{html_lib.escape(self.scenario_name)} — Test reports</title>
  <style>
    :root {{
      --bg: #0f1117;
      --surface: #1a1d27;
      --surface2: #22263a;
      --border: #2e3350;
      --text: #e2e8f0;
      --muted: #8892b0;
      --accent: #64ffda;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 2rem;
    }}
    a {{ color: var(--accent); text-decoration: none; }}

    /* ── Header ── */
    .header {{
      background: linear-gradient(135deg, var(--surface) 0%, var(--surface2) 100%);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 2rem 2.5rem;
      margin-bottom: 1.5rem;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 1.5rem;
    }}
    .header-left {{ flex: 1; min-width: 280px; }}
    .suite-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: .12em;
      color: var(--accent);
      margin-bottom: .4rem;
    }}
    .scenario-title {{
      font-size: 1.6rem;
      font-weight: 700;
      line-height: 1.2;
      margin-bottom: .5rem;
    }}
    .scenario-desc {{
      color: var(--muted);
      font-size: .9rem;
    }}
    .status-badge {{
      padding: .55rem 1.4rem;
      border-radius: 999px;
      font-weight: 700;
      font-size: 1.1rem;
      color: #fff;
      background: {status_color};
      box-shadow: 0 0 18px {status_color}55;
      letter-spacing: .06em;
    }}

    /* ── Meta grid ── */
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: .75rem;
      margin-bottom: 1.5rem;
    }}
    .meta-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem 1.25rem;
    }}
    .meta-card .label {{
      font-size: .7rem;
      text-transform: uppercase;
      letter-spacing: .1em;
      color: var(--muted);
      margin-bottom: .3rem;
    }}
    .meta-card .value {{
      font-size: 1.05rem;
      font-weight: 600;
      color: var(--text);
    }}

    /* ── Error block ── */
    .error-block {{
      background: #2a1215;
      border-left: 4px solid #dc3545;
      border-radius: 8px;
      padding: 1rem 1.25rem;
      margin-bottom: 1.5rem;
      color: #f1aeb5;
      font-size: .9rem;
    }}

    /* ── Legend ── */
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: .5rem;
      margin-bottom: 1.5rem;
    }}
    .legend-item {{
      padding: .3rem .8rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: .8rem;
      color: var(--muted);
    }}

    /* ── Steps ── */
    .steps-title {{
      font-size: 1rem;
      font-weight: 600;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .1em;
      margin-bottom: .75rem;
    }}
    .step {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      margin-bottom: .75rem;
      overflow: hidden;
      transition: box-shadow .15s;
    }}
    .step:hover {{ box-shadow: 0 0 0 1px var(--accent)44; }}
    .step-header {{
      display: flex;
      align-items: center;
      gap: .75rem;
      padding: .7rem 1rem;
      cursor: pointer;
      user-select: none;
      background: var(--surface2);
    }}
    .step-index {{
      font-size: .7rem;
      color: var(--muted);
      min-width: 2rem;
      text-align: right;
    }}
    .agent-chip {{
      font-size: .75rem;
      font-weight: 700;
      padding: .25rem .7rem;
      border-radius: 999px;
      color: #fff;
      white-space: nowrap;
    }}
    .step-preview {{
      flex: 1;
      font-size: .85rem;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .step-time {{
      font-size: .7rem;
      color: var(--muted);
      white-space: nowrap;
    }}
    .toggle-icon {{
      font-size: .75rem;
      color: var(--muted);
      transition: transform .2s;
    }}
    .step-body {{
      padding: 1rem 1.2rem;
      display: none;
      border-top: 1px solid var(--border);
    }}
    .step-body.open {{ display: block; }}
    .step-body pre {{
      white-space: pre-wrap;
      word-break: break-word;
      font-family: 'Cascadia Code', 'Consolas', monospace;
      font-size: .82rem;
      color: var(--text);
      line-height: 1.6;
    }}

    /* ── Footer ── */
    .footer {{
      margin-top: 2rem;
      text-align: center;
      font-size: .75rem;
      color: var(--muted);
    }}
  </style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <div class="header-left">
      <div class="suite-label">🧪 {html_lib.escape(self.suite_name)}</div>
      <div class="scenario-title">{html_lib.escape(self.scenario_name)}</div>
      {f'<div class="scenario-desc">{html_lib.escape(self.description)}</div>' if self.description else ''}
    </div>
    <div class="status-badge">{self._status}</div>
  </div>

  <!-- Meta -->
  <div class="meta-grid">
    <div class="meta-card">
      <div class="label">Started</div>
      <div class="value">{self._start_time.strftime('%Y-%m-%d %H:%M:%S') if self._start_time else '—'}</div>
    </div>
    <div class="meta-card">
      <div class="label">Finished</div>
      <div class="value">{self._end_time.strftime('%Y-%m-%d %H:%M:%S') if self._end_time else '—'}</div>
    </div>
    <div class="meta-card">
      <div class="label">Duration</div>
      <div class="value">{self._duration_str()}</div>
    </div>
    <div class="meta-card">
      <div class="label">Total Steps</div>
      <div class="value">{len(self._steps)}</div>
    </div>
    <div class="meta-card">
      <div class="label">Status</div>
      <div class="value" style="color:{status_color}">{self._status}</div>
    </div>
  </div>

  {error_block}

  <!-- Agent legend -->
  <div class="legend">{agent_legend}</div>

  <!-- Steps -->
  <div class="steps-title">📋 Conversation Steps</div>
  {steps_html}

  <div class="footer">
    Generated by AgenticAI Reporter &nbsp;•&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  </div>

  <script>
    document.querySelectorAll('.step-header').forEach(function(hdr) {{
      hdr.addEventListener('click', function() {{
        var body = hdr.nextElementSibling;
        var icon = hdr.querySelector('.toggle-icon');
        body.classList.toggle('open');
        icon.textContent = body.classList.contains('open') ? '▲' : '▼';
      }});
    }});
    // Open first step by default
    var first = document.querySelector('.step-body');
    if (first) {{
      first.classList.add('open');
      first.previousElementSibling.querySelector('.toggle-icon').textContent = '▲';
    }}
  </script>
</body>
</html>"""

    def _render_step(self, index: int, step: StepRecord) -> str:
        color = _agent_color(step.agent)
        elapsed = f"+{step.elapsed_seconds:.1f}s" if step.elapsed_seconds is not None else ""
        preview = step.content.replace("\n", " ")[:120]
        escaped_content = html_lib.escape(step.content)
        
        # Extract screenshot path hints from tool output/messages.
        screenshot_html = ""
        screenshot_rel_path = None

        if "reports/Screenshots/" in step.content:
            try:
                filename = step.content.split("reports/Screenshots/")[1].strip().split()[0]
                filename = filename.rstrip(")]")
                screenshot_rel_path = f"../Screenshots/{filename}"
            except Exception:
                pass
        elif "reports/screenshots/" in step.content:
            try:
                filename = step.content.split("reports/screenshots/")[1].strip().split()[0]
                filename = filename.rstrip(")]")
                screenshot_rel_path = f"../screenshots/{filename}"
            except Exception:
                pass
        elif "![" in step.content and ".png" in step.content:
            match = re.search(r"\(([^)]+\.png)\)", step.content)
            if match:
                raw_path = match.group(1).replace("\\", "/")
                if raw_path.startswith("reports/Screenshots/"):
                    screenshot_rel_path = f"../{raw_path.replace('reports/', '', 1)}"
                elif raw_path.startswith("reports/screenshots/"):
                    screenshot_rel_path = f"../{raw_path.replace('reports/', '', 1)}"

        if screenshot_rel_path:
            screenshot_html = (
                f'<div class="screenshot-wrap"><img src="{screenshot_rel_path}" alt="Screenshot" '
                'style="max-width: 100%; border: 1px solid var(--border); border-radius: 8px; margin-top: 1rem;"></div>'
            )

        return f"""  <div class="step">
    <div class="step-header">
      <span class="step-index">#{index + 1}</span>
      <span class="agent-chip" style="background:{color}">{html_lib.escape(step.agent)}</span>
      <span class="step-preview">{html_lib.escape(preview)}</span>
      <span class="step-time">{elapsed}</span>
      <span class="toggle-icon">▼</span>
    </div>
    <div class="step-body">
      <pre>{escaped_content}</pre>
      {screenshot_html}
    </div>
  </div>"""


# ---------------------------------------------------------------------------
# SuiteReporter  –  aggregates multiple ScenarioReporters → one suite report
# ---------------------------------------------------------------------------

class SuiteReporter:
    """
    Collects results from multiple ScenarioReporter instances and writes
    a single suite-level HTML report.

    Usage
    -----
    suite = SuiteReporter("AgenticAI Regression Suite")

    rep1 = ScenarioReporter("Scenario 1", suite_name=suite.suite_name)
    # ... run scenario 1 ...
    suite.add(rep1)

    rep2 = ScenarioReporter("Scenario 2", suite_name=suite.suite_name)
    # ... run scenario 2 ...
    suite.add(rep2)

    suite.save_report()   # → reports/result/suite_<timestamp>.html
    """

    def __init__(self, suite_name: str = "AgenticAI Test Suite"):
        self.suite_name = suite_name
        self._reporters: list[ScenarioReporter] = []
        self._created_at = datetime.now()

    def add(self, reporter):
        """
        Register a completed scenario result.
        Accepts a ScenarioReporter instance or any object that exposes the
        same attributes (scenario_name, description, suite_name, _status,
        _steps, _start_time, _end_time, _duration_str()).
        """
        self._reporters.append(reporter)

    def save_report(self) -> str:
        """Write suite HTML report and return its absolute path."""
        os.makedirs(_REPORT_DIR, exist_ok=True)
        ts = self._created_at.strftime("%Y%m%d_%H%M%S")
        filename = f"suite_{_safe_filename(self.suite_name)}_{ts}.html"
        filepath = os.path.abspath(os.path.join(_REPORT_DIR, filename))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self._render_suite_html())

        print(f"[SuiteReporter] 📊 Suite report saved → {filepath}")
        return filepath

    # ------------------------------------------------------------------
    def _total(self) -> int: return len(self._reporters)
    def _passed(self) -> int: return sum(1 for r in self._reporters if r._status == "PASS")
    def _failed(self) -> int: return sum(1 for r in self._reporters if r._status == "FAIL")
    def _pass_rate(self) -> str:
        if not self._reporters: return "0%"
        return f"{100 * self._passed() // self._total()}%"

    def _render_suite_html(self) -> str:
        rows = "\n".join(self._render_row(i, r) for i, r in enumerate(self._reporters))
        overall_color = _STATUS_COLORS["PASS"] if self._failed() == 0 else _STATUS_COLORS["FAIL"]
        overall_label = "ALL PASS" if self._failed() == 0 else f"{self._failed()} FAILED"

        # Build individual report links
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{html_lib.escape(self.suite_name)} — Suite reports</title>
  <style>
    :root {{
      --bg: #0f1117; --surface: #1a1d27; --surface2: #22263a;
      --border: #2e3350; --text: #e2e8f0; --muted: #8892b0; --accent: #64ffda;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); padding: 2rem; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    .header {{
      background: linear-gradient(135deg, var(--surface), var(--surface2));
      border: 1px solid var(--border); border-radius: 12px;
      padding: 2rem 2.5rem; margin-bottom: 1.5rem;
      display: flex; flex-wrap: wrap; align-items: center; gap: 1.5rem;
    }}
    .suite-title {{ font-size: 1.8rem; font-weight: 700; }}
    .suite-date {{ font-size: .85rem; color: var(--muted); margin-top: .3rem; }}
    .overall-badge {{
      padding: .55rem 1.6rem; border-radius: 999px; font-weight: 700;
      font-size: 1rem; color: #fff; background: {overall_color};
      box-shadow: 0 0 18px {overall_color}55;
    }}

    .summary-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(130px,1fr));
      gap: .75rem; margin-bottom: 1.5rem;
    }}
    .sum-card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 10px; padding: 1rem 1.25rem; text-align: center;
    }}
    .sum-card .lbl {{ font-size:.7rem; text-transform:uppercase; letter-spacing:.1em; color:var(--muted); margin-bottom:.3rem; }}
    .sum-card .val {{ font-size: 1.6rem; font-weight: 700; }}

    .progress-bar-wrap {{ margin-bottom: 1.5rem; }}
    .progress-label {{ font-size: .8rem; color: var(--muted); margin-bottom: .4rem; }}
    .progress-bar-bg {{
      height: 10px; background: var(--surface2); border-radius: 999px; overflow: hidden;
    }}
    .progress-bar-fill {{
      height: 100%; background: {overall_color};
      width: {self._pass_rate()}; border-radius: 999px;
      transition: width .5s;
    }}

    table {{ width: 100%; border-collapse: collapse; }}
    thead tr {{ background: var(--surface2); }}
    th, td {{
      padding: .75rem 1rem; text-align: left;
      border-bottom: 1px solid var(--border); font-size: .9rem;
    }}
    th {{ font-size: .75rem; text-transform: uppercase; letter-spacing:.08em; color: var(--muted); }}
    tbody tr:hover {{ background: var(--surface2); }}
    .badge {{
      display: inline-block; padding: .2rem .7rem; border-radius: 999px;
      font-size: .75rem; font-weight: 700; color: #fff;
    }}
    .footer {{ margin-top: 2rem; text-align: center; font-size: .75rem; color: var(--muted); }}
  </style>
</head>
<body>

  <div class="header">
    <div style="flex:1">
      <div class="suite-title">🧪 {html_lib.escape(self.suite_name)}</div>
      <div class="suite-date">Generated: {self._created_at.strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
    <div class="overall-badge">{overall_label}</div>
  </div>

  <div class="summary-grid">
    <div class="sum-card">
      <div class="lbl">Total</div>
      <div class="val">{self._total()}</div>
    </div>
    <div class="sum-card">
      <div class="lbl">Passed</div>
      <div class="val" style="color:{_STATUS_COLORS['PASS']}">{self._passed()}</div>
    </div>
    <div class="sum-card">
      <div class="lbl">Failed</div>
      <div class="val" style="color:{_STATUS_COLORS['FAIL']}">{self._failed()}</div>
    </div>
    <div class="sum-card">
      <div class="lbl">Pass Rate</div>
      <div class="val" style="color:{overall_color}">{self._pass_rate()}</div>
    </div>
  </div>

  <div class="progress-bar-wrap">
    <div class="progress-label">Pass Rate — {self._pass_rate()}</div>
    <div class="progress-bar-bg"><div class="progress-bar-fill"></div></div>
  </div>

  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Scenario</th>
        <th>Suite</th>
        <th>Status</th>
        <th>Steps</th>
        <th>Duration</th>
        <th>Started</th>
        <th>reports</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <div class="footer">
    AgenticAI SuiteReporter &nbsp;•&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  </div>
</body>
</html>"""

    def _render_row(self, index: int, rep: ScenarioReporter) -> str:
        color = _STATUS_COLORS.get(rep._status, "#6c757d")
        started = rep._start_time.strftime("%H:%M:%S") if rep._start_time else "—"
        # Try to find the individual report file
        ts_str = rep._start_time.strftime("%Y%m%d_%H%M%S") if rep._start_time else ""
        ind_filename = f"{_safe_filename(rep.scenario_name)}_{ts_str}.html"
        ind_path = os.path.join(_REPORT_DIR, ind_filename)
        link = (
            f'<a href="{ind_filename}" target="_blank">Open ↗</a>'
            if os.path.exists(ind_path) else "—"
        )
        return f"""      <tr>
        <td>{index + 1}</td>
        <td><strong>{html_lib.escape(rep.scenario_name)}</strong>
          {"<br><small style='color:var(--muted)'>" + html_lib.escape(rep.description) + "</small>" if rep.description else ""}
        </td>
        <td style="color:var(--muted)">{html_lib.escape(rep.suite_name)}</td>
        <td><span class="badge" style="background:{color}">{rep._status}</span></td>
        <td>{len(rep._steps)}</td>
        <td>{rep._duration_str()}</td>
        <td>{started}</td>
        <td>{link}</td>
      </tr>"""




