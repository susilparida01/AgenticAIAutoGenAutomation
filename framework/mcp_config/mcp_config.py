"""
This module provides a configuration class for creating McpWorkbench instances.

The McpConfig class contains static methods for creating McpWorkbench instances 
for different tools like MySQL, REST API, Excel, and Filesystem. Each method 
configures the necessary parameters for the StdioServer and returns a 
McpWorkbench instance.
"""
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench
from libs.config_reader import ConfigReader

class McpConfig:
    """
    A configuration class for creating McpWorkbench instances.
    """

    @staticmethod
    def get_mysql_workbench():
        """
        Get a MySQL MCP workbench instance.

        This method configures the StdioServerParams for a MySQL database connection.
        It sets the command to run the MySQL MCP server and the environment variables
        for the database connection.

        Returns:
            McpWorkbench: An McpWorkbench instance configured for MySQL.
        """
        mysql_server_params = StdioServerParams(
            command=ConfigReader.get_uv_path(),
            args=[
                "--directory",
                ConfigReader.get_site_packages_path(),
                "run",
                "mysql_mcp_server"
            ],
            env={
                "MYSQL_HOST": ConfigReader.get_property("MYSQL_HOST"),
                "MYSQL_PORT": ConfigReader.get_property("MYSQL_PORT"),
                "MYSQL_USER": ConfigReader.get_property("MYSQL_USER"),
                "MYSQL_PASSWORD": ConfigReader.get_property("MYSQL_PASSWORD"),
                "MYSQL_DATABASE": ConfigReader.get_property("MYSQL_DATABASE")
            } )
        return McpWorkbench( server_params=mysql_server_params )

    @staticmethod
    def get_rest_api_workbench():
        """
        Get a REST API MCP workbench instance.

        This method configures the StdioServerParams for a REST API connection.
        It sets the command to run the REST API MCP server and the environment
        variables for the base URL and headers.

        Returns:
            McpWorkbench: An McpWorkbench instance configured for a REST API.
        """
        rest_api_server_params = StdioServerParams(
            command="npx",
            args=[
                "-y",
                "dkmaker-mcp-rest-api"
            ],
            env={
                "REST_BASE_URL": ConfigReader.get_property("REST_BASE_URL"),
                "HEADER_Accept": "application/json"
            } )
        return McpWorkbench( rest_api_server_params )

    @staticmethod
    def get_excel_workbench():
        """
        Get an Excel MCP workbench instance.

        This method configures the StdioServerParams for an Excel file connection.
        It sets the command to run the Excel MCP server and the environment
        variables for the paging cells limit.

        Returns:
            McpWorkbench: An McpWorkbench instance configured for Excel.
        """
        excel_server_params = StdioServerParams(
            command="npx",
            args=["--yes", "@negokaz/excel-mcp-server"],
            env={
                "EXCEL_MCP_PAGING_CELLS_LIMIT": "4000"
            },
            read_timeout_seconds=60
        )
        return McpWorkbench( server_params=excel_server_params )

    @staticmethod
    def get_filesystem_workbench():
        """
        Get a Filesystem MCP workbench instance.

        This method configures the StdioServerParams for a filesystem connection.
        It sets the command to run the Filesystem MCP server and the path to the
        directory to be served.

        Returns:
            McpWorkbench: An McpWorkbench instance configured for the filesystem.
        """
        filesystem_server_params = StdioServerParams(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", ConfigReader.get_property("FILESYSTEM_PATH")],
            read_timeout_seconds=60
        )
        return McpWorkbench( server_params=filesystem_server_params )

    @staticmethod
    def get_jira_workbench():
        """
        Get a Jira MCP workbench instance.

        This method configures the StdioServerParams for a Jira connection.
        It sets the command to run the Jira MCP server via Docker.

        Returns:
            McpWorkbench: An McpWorkbench instance configured for Jira.
        """
        jira_server_params = StdioServerParams(
            command="docker",
            args=[
                "run", "-i", "--rm",
                "--dns", "8.8.8.8", "--dns", "1.1.1.1",
                "-e", f"JIRA_URL={ConfigReader.get_property('JIRA_URL')}",
                "-e", f"JIRA_USERNAME={ConfigReader.get_property('JIRA_USERNAME')}",
                "-e", f"JIRA_API_TOKEN={ConfigReader.get_property('JIRA_API_TOKEN')}",
                "-e", f"JIRA_PROJECTS_FILTER={ConfigReader.get_property('JIRA_PROJECTS_FILTER')}",
                "ghcr.io/sooperset/mcp-atlassian:latest"
            ]
        )
        return McpWorkbench( server_params=jira_server_params )

    @staticmethod
    def get_playwright_workbench():
        """
        Get a Playwright MCP workbench instance.

        This method configures the StdioServerParams for a Playwright connection.
        It sets the command to run the Playwright MCP server.

        Returns:
            McpWorkbench: An McpWorkbench instance configured for Playwright.
        """
        headless = ConfigReader.get_bool_property("PLAYWRIGHT_HEADLESS", default=False)
        headless_value = "true" if headless else "false"
        print(f"[McpConfig] PLAYWRIGHT_HEADLESS={headless_value} (from config.properties)")

        playwright_server_params = StdioServerParams(
            command="npx",
            args=["-y", "@playwright/mcp@latest", "--browser", "chrome", "--no-sandbox"],
            env={
                "PLAYWRIGHT_HEADLESS": headless_value
            },
            read_timeout_seconds=60
        )
        return McpWorkbench( server_params=playwright_server_params )
