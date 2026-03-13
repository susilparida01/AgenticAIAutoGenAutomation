import os
from datetime import datetime

from autogen_core.tools import FunctionTool

async def capture_screenshot(scenario_name: str, step_name: str) -> str:
    """
    Generates a canonical screenshot path under reports/Screenshots.
    The agent should pass this path to browser_take_screenshot(filename=...).
    
    Args:
        scenario_name: The name of the scenario (e.g. 'Valid Login').
        step_name: A description of the step (e.g. 'dashboard_view').
    """
    # Canonical screenshot directory for all scenarios/reports.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    screenshot_dir = os.path.join(project_root, 'reports', 'Screenshots')
    
    # Create the directory if it doesn't exist
    if not os.path.exists(screenshot_dir):
        os.makedirs(screenshot_dir, exist_ok=True)
        
    # Generate a unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_scenario = scenario_name.replace(" ", "_").lower()
    safe_step = step_name.replace(" ", "_").lower()
    filename = f"{safe_scenario}_{safe_step}_{timestamp}.png"
    rel_path = f"reports/Screenshots/{filename}"
    
    try:
        # This tool only standardizes path output; actual capture is done by browser_take_screenshot.
        return f"Use browser_take_screenshot with filename: {rel_path}"
    except Exception as e:
        return f"Failed to capture screenshot: {str(e)}"

# Wrap it for AutoGen
capture_agent_screenshot = FunctionTool(
    capture_screenshot,
    name="capture_agent_screenshot",
    description="Generates a reports/Screenshots filename for browser_take_screenshot."
)
