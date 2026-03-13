import asyncio

from autogen_agentchat.conditions import TextMentionTermination

# Discovered automatically by run_suite.py
SCENARIO_META = {
    "name":        "Scenario_03 - MySQL Department Data Query",
    "description": "Connects to the bakery_hr database and verifies that Bakery, Sales and Finance departments exist.",
}

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from framework.agentfactory.agentFactory import AgentFactory
from libs.config_reader import ConfigReader
from libs.report_manager import run_scenario_with_report

import os
# Load environment variables from config
ConfigReader.load_to_environ([
    "OPENAI_API_KEY", "MODEL_NAME", "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"
])


async def main():
    model_name = os.getenv("MODEL_NAME")
    model_client = OpenAIChatCompletionClient(model=model_name)
    factory = AgentFactory(model_client)

    database_agent = await factory.create_database_agent(
        system_message=("""
                                        You are a MySQL database automation specialist.
                                        
                                        Goal:
                                        Retrieve and validate table information using database tools.
                                        
                                        Tasks:
                                        1. Connect to the MySQL database: bakery_hr
                                        2. Query the table: departments
                                        3. Retrieve department records.
                                        4. Validate that the table contains data.
                                        5. Display results in structured format (rows/columns).
                                        
                                        Validation Rules:
                                        - Confirm table exists.
                                        - Confirm records are returned.
                                        - If no records are found, report the issue.
                                        
                                        Output:
                                        Provide the department table data and validation result.
                                        
                                        Finish by writing: DEPARTMENT_DATA_READY
                                    """)
    )

    team = RoundRobinGroupChat(
        participants=[database_agent],
        termination_condition=TextMentionTermination("DEPARTMENT_DATA_READY"),
    )

    await run_scenario_with_report(
        team=team,
        model_client=model_client,
        scenario_name=SCENARIO_META["name"],
        description=SCENARIO_META["description"],
        task=(
            """
            Connect to the MySQL database: bakery_hr.
            
            Actions:
            1. Query the table: departments.
            2. Retrieve department name data.
            3. Print the department records in a clear table format.
            
            Validation:
            1. Verify the table contains the following department names:
               - Bakery
               - Sales
               - Finance
            2. Confirm all three departments exist in the results.
            
            Output:
            - Display the retrieved department data.
            - Report validation result:
              PASS if Bakery, Sales, and Finance are present.
              FAIL if any department is missing.
            
            End with: DEPARTMENT_VALIDATION_COMPLETE            
            """
        ),
        pass_condition_text="DEPARTMENT_DATA_READY",
    )


if __name__ == "__main__":
    asyncio.run(main())
