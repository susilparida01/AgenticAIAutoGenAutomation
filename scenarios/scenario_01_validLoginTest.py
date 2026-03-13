import asyncio
import os
import sys

# Add project root to sys.path to allow importing from framework and libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autogen_agentchat.conditions import TextMentionTermination

# Discovered automatically by run_suite.py
SCENARIO_META = {
    "name":        "Scenario 01 - Valid Login Test",
    "description": "Navigates to the target web app, log in and validate login successful.",
}

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from framework.agentfactory.agentFactory import AgentFactory
from libs.config_reader import ConfigReader
from libs.report_manager import run_scenario_with_report

# Load environment variables from config
ConfigReader.load_to_environ([
    "OPENAI_API_KEY", "MODEL_NAME", "BROWSER_URL", "BROWSER_USERNAME", "BROWSER_PASSWORD"
])


async def main():
    model_name = os.getenv("MODEL_NAME")
    model_client = OpenAIChatCompletionClient(model=model_name)
    factory = AgentFactory(model_client)

    browser_url  = os.getenv("BROWSER_URL")
    browser_user = os.getenv("BROWSER_USERNAME")
    browser_pass = os.getenv("BROWSER_PASSWORD")

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    screenshots_dir = os.path.join(project_root, "Reports", "Screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    dashboard_shot = os.path.join(screenshots_dir, "scenario_01_dashboard.png").replace("\\", "/")
    login_page_shot = os.path.join(screenshots_dir, "scenario_01_login_page.png").replace("\\", "/")

    completion_token = "VALID_LOGIN_VERIFIED"

    automation_agent = await factory.create_automation_agent(system_message=(f"""
                                                You are a Playwright automation expert using MCP browser tools.

                                                Execute UI automation steps exactly as provided.

                                                Rules:
                                                1. You MUST use Playwright MCP tools to execute actions in a real browser.
                                                2. Follow the task instructions step by step.
                                                3. Use browser_wait_for before every interaction with element.
                                                4. Capture an evidence screenshot using browser_take_screenshot.
                                                5. Validate expected results (success or error messages).
                                                6. Clearly report PASS/FAIL for each validation.
                                                7. Stop only after all steps are completed.

                                                Final response format:
                                                - Login Status: PASS|FAIL
                                                - Logout Status: PASS|FAIL
                                                - Dashboard Screenshot: <absolute path>
                                                - Login Page Screenshot: <absolute path>
                                                Only after completing all UI actions, end with token: {completion_token}

                                            """))

    team = RoundRobinGroupChat(
        participants=[automation_agent],
        termination_condition=TextMentionTermination(completion_token),
    )

    await run_scenario_with_report(
        team=team,
        model_client=model_client,
        scenario_name=SCENARIO_META["name"],
        description=SCENARIO_META["description"],
        task=f"""
                    Execute this UI flow using Playwright MCP tools only:

                    1. Navigate to {browser_url}. Wait for the login page is ready.
                    2. Enter username: {browser_user}
                    3. Enter password: {browser_pass}
                    4. Click Login. Wait for dashboard page.
                    5. Capture screenshot with:
                       browser_take_screenshot(filename="{dashboard_shot}")
                    6. Click Logout. Wait for login page.
                    5. browser_take_screenshot(filename="{login_page_shot}")

                    Return the final result in the required format.
                    Use the completion token from your system instructions only after all steps are done.
                """,
        pass_condition_text=completion_token,
    )


if __name__ == "__main__":
    asyncio.run(main())
