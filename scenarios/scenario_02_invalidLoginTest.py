import asyncio
import os
import sys

# Add project root to sys.path to allow importing from framework and libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autogen_agentchat.conditions import TextMentionTermination

# Discovered automatically by run_suite.py
SCENARIO_META = {
    "name":        "Scenario 02 - Invalid Login Test",
    "description": "Navigates to the target web app, logs in with invalid credentials and validate login unsuccessful.",
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

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    screenshots_dir = os.path.join(project_root, "Reports", "Screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    error_shot = os.path.join(screenshots_dir, "scenario_02_invalid_login_error.png").replace("\\", "/")

    completion_token = "INVALID_LOGIN_VERIFIED"

    automation_agent = await factory.create_automation_agent(system_message=(f"""
    
                                                You are a Playwright automation expert using MCP browser tools.
                                                
                                                Execute UI automation steps exactly as provided.  
                                                                                              
                                                Rules:
                                                1. You MUST use Playwright MCP tools to execute actions in a real browser.
                                                2. First call browser_navigate to open the URL.
                                                3. Use browser_wait_for before every interaction.
                                                4. Perform invalid login and verify the visible error message after clicking Login.
                                                5. Capture an evidence screenshot using browser_take_screenshot.
                                                6. Do not claim PASS unless the browser actions were actually executed.

                                                Final response format:
                                                - Invalid Login Status: PASS|FAIL
                                                - Evidence Screenshot: <absolute path>
                                                - End with token: {completion_token}
                                                
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

                    1. Navigate to {browser_url} and ensure the login page is ready.
                    2. Enter username: admin
                    3. Enter password: 123admin123
                    4. Click Login.
                    5. Wait for and validate a login failure message is visible.
                    6. Capture screenshot with:
                       browser_take_screenshot(filename="{error_shot}")

                    Return the final result in the required format.
                """,
        pass_condition_text=completion_token,
    )


if __name__ == "__main__":
    asyncio.run(main())
