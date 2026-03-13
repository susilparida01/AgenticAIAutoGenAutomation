from typing import Any, List, Mapping, Optional, Sequence, Type
from autogen_agentchat.agents import AssistantAgent
from autogen_core.tools import Workbench, ToolSchema, ToolResult, BaseTool
from pydantic import BaseModel
from framework.mcp_config.mcp_config import McpConfig
from libs.screenshot_tool import capture_agent_screenshot

class LocalToolWorkbench(Workbench):
    def __init__(self, tools: List[BaseTool]):
        super().__init__()
        self._tools = {tool.name: tool for tool in tools}

    async def list_tools(self) -> List[ToolSchema]:
        return [tool.schema for tool in self._tools.values()]

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        cancellation_token: Optional[Any] = None,
        call_id: str | None = None,
    ) -> ToolResult:
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found")
        
        # BaseTool expects arguments as its args_type (e.g. BaseModel or specific subclass)
        tool = self._tools[name]
        # For FunctionTool, we can often just pass the dict or the model
        # Most AutoGen tools handle run_json or similar
        result = await tool.run_json(arguments or {}, cancellation_token)
        # Workbench.call_tool expects ToolResult or just the result? 
        # Actually, let's see what ToolResult is.
        return result

    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def reset(self) -> None: pass
    async def save_state(self) -> Mapping[str, Any]: return {}
    async def load_state(self, state: Mapping[str, Any]) -> None: pass

class AgentFactory:

    def __init__(self, model_client):
        self.model_client = model_client
        self.mcp_config = McpConfig()

    async def create_issue_analyst(self, system_message):
        """Create a Bug Analyst agent"""
        jira_workbench = self.mcp_config.get_jira_workbench()
        return AssistantAgent(
            name="BugAnalyst",
            model_client=self.model_client,
            workbench=jira_workbench,
            system_message=system_message
        )

    async def create_automation_agent(self, system_message):
        """Create an Automation agent"""
        playwright_workbench = self.mcp_config.get_playwright_workbench()
        local_workbench = LocalToolWorkbench(tools=[capture_agent_screenshot])

        return AssistantAgent(
            name="AutomationAgent",
            model_client=self.model_client,
            workbench=[playwright_workbench, local_workbench],
            system_message=system_message
        )

    async def create_database_agent(self, system_message):
        database_workbench = self.mcp_config.get_mysql_workbench()
        database_agent = AssistantAgent( 
            name="DatabaseAgent", 
            model_client=self.model_client,
            workbench=database_workbench,
            system_message=system_message 
        )
        return database_agent

    async def create_api_agent(self,system_message):
        rest_api_workbench = self.mcp_config.get_rest_api_workbench()
        file_system_workbench = self.mcp_config.get_filesystem_workbench()
        
        api_agent = AssistantAgent(
            name="APIAgent",
            model_client=self.model_client,
            workbench=[rest_api_workbench, file_system_workbench],
            system_message=system_message
        )
        return api_agent

    async def create_excel_agent(self, system_message=None):
        """Create an Excel agent with custom system message"""
        excel_workbench = self.mcp_config.get_excel_workbench()

        excel_agent = AssistantAgent(
            name="ExcelAgent",
            model_client=self.model_client,
            workbench=excel_workbench,
            system_message=system_message
        )

        return excel_agent
