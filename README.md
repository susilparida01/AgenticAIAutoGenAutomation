# AgenticAI AutoGen Framework

A multi-agent automation framework built on top of **Microsoft AutoGen** (`autogen-agentchat` / `autogen-ext`). It orchestrates AI agents that can drive a browser with Playwright, query MySQL, call REST APIs, work with Excel files, and integrate with Jira through MCP workbenches.

## Table of Contents

- [Overview](#overview)
- [Current Project Scope](#current-project-scope)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Key Components](#key-components)
  - [`ConfigReader`](#configreader---libsconfig_readerpy)
  - [`McpConfig`](#mcpconfig---frameworkmcp_configmcp_configpy)
  - [`AgentFactory`](#agentfactory---frameworkagentfactoryagentfactorypy)
  - [`ScenarioReporter` and `SuiteReporter`](#scenarioreporter-and-suitereporter---libsreporterpy)
- [Scenarios](#scenarios)
  - [`scenario_01_validLoginTest.py`](#scenario_01_validlogintestpy)
  - [`scenario_02_invalidLoginTest.py`](#scenario_02_invalidlogintestpy)
  - [`scenario_03_databaseTableDepartmentTest.py`](#scenario_03_databasetabledepartmenttestpy)
  - [`scenario_04_databaseTableEmployeeTest.py`](#scenario_04_databasetableemployeetestpy)
- [Configuration](#configuration)
- [Reports and Screenshots](#reports-and-screenshots)
- [Setup](#setup)
- [How to Run](#how-to-run)
- [Preparing for GitHub Check-in](#preparing-for-github-check-in)
- [Notes and Known Behavior](#notes-and-known-behavior)

---

## Overview

This repository demonstrates an **agentic automation** pattern where one or more AutoGen agents collaborate to complete test or validation tasks.

Each agent is configured with:

- a **role** (`system_message`)
- a **model client** (`OpenAIChatCompletionClient`)
- one or more **MCP workbenches** for tool use
- a **termination keyword** used by the scenario team to stop execution

The framework currently focuses on:

- **UI automation** through Playwright MCP
- **database validation** through MySQL MCP
- **HTML reporting** for both individual scenarios and the whole suite

---

## Current Project Scope

The codebase contains reusable agent factories for:

- Playwright browser automation
- MySQL queries
- REST API access
- Excel access
- Jira access

However, the **current runnable suite** in `scenarios/` is centered on:

1. Valid login UI automation
2. Invalid login UI automation
3. MySQL department data validation
4. MySQL employee data validation

So the framework is broader than the currently committed scenarios.

---

## Architecture

```text
Scenario file (scenarios/scenario_*.py)
    -> creates model client
    -> asks AgentFactory for one or more agents
    -> builds RoundRobinGroupChat
    -> runs via run_scenario_with_report(...)
    -> writes HTML report to reports/result/

run_suite.py
    -> auto-discovers all scenarios/scenario*.py
    -> executes them sequentially
    -> writes per-scenario reports
    -> writes one suite report
```

High-level component flow:

```text
scenarios/*.py
   -> AgentFactory
      -> McpConfig
         -> ConfigReader
            -> config/config.properties
```

---

## Project Structure

```text
AgenticAIAutoGen/
├── config/
│   └── config.properties
├── Data/
│   └── files/
├── framework/
│   ├── agentfactory/
│   │   └── agentFactory.py
│   └── mcp_config/
│       └── mcp_config.py
├── libs/
│   ├── config_reader.py
│   ├── report_manager.py
│   ├── reporter.py
│   └── screenshot_tool.py
├── reports/
│   ├── result/
│   └── Screenshots/
├── scenarios/
│   ├── scenario_01_validLoginTest.py
│   ├── scenario_02_invalidLoginTest.py
│   ├── scenario_03_databaseTableDepartmentTest.py
│   └── scenario_04_databaseTableEmployeeTest.py
├── requirements.txt
├── run_suite.py
└── README.md
```

---

## Key Components

### `ConfigReader` - `libs/config_reader.py`

`ConfigReader` reads `config/config.properties` and exposes helper methods to the rest of the framework.

Main methods:

- `get_property(key, default=None)`
- `get_bool_property(key, default=False)`
- `get_uv_path()`
- `get_site_packages_path()`
- `load_to_environ(keys=None)`

Notable behavior:

- `config.properties` is treated as a flat `key=value` file.
- A temporary `[DEFAULT]` section is prepended internally so `ConfigParser` can parse it.
- `get_bool_property(...)` normalizes values like `true/false`, `1/0`, `yes/no`, `on/off`.

---

### `McpConfig` - `framework/mcp_config/mcp_config.py`

`McpConfig` builds the MCP workbenches used by agents.

Available workbenches:

- `get_mysql_workbench()`
- `get_rest_api_workbench()`
- `get_excel_workbench()`
- `get_filesystem_workbench()`
- `get_jira_workbench()`
- `get_playwright_workbench()`

#### Playwright behavior

`get_playwright_workbench()` currently launches:

- `@playwright/mcp@latest`
- browser channel: `chrome`
- `--no-sandbox`

Headless mode is controlled centrally through:

- `PLAYWRIGHT_HEADLESS=false` in `config/config.properties`

At runtime, the framework logs the resolved value, for example:

```text
[McpConfig] PLAYWRIGHT_HEADLESS=false (from config.properties)
```

This makes it easier to confirm whether the browser is intended to be headed or headless during a run.

---

### `AgentFactory` - `framework/agentfactory/agentFactory.py`

`AgentFactory` creates preconfigured `AssistantAgent` instances.

Available factory methods:

- `create_issue_analyst(system_message)` -> `BugAnalyst`
- `create_automation_agent(system_message)` -> `AutomationAgent`
- `create_database_agent(system_message)` -> `DatabaseAgent`
- `create_api_agent(system_message)` -> `APIAgent`
- `create_excel_agent(system_message)` -> `ExcelAgent`

Important detail:

- `create_automation_agent(...)` attaches both:
  - Playwright MCP workbench
  - local screenshot helper tool `capture_agent_screenshot`

The screenshot helper does **not** capture images itself. It generates a canonical screenshot filename/path that the agent can pass to Playwright's `browser_take_screenshot(...)` tool.

---

### `ScenarioReporter` and `SuiteReporter` - `libs/reporter.py`

Reporting is built into the framework.

- `ScenarioReporter` captures messages from one scenario run and writes one HTML report.
- `SuiteReporter` aggregates all discovered scenario results into a single suite HTML report.

Report output directory:

- `reports/result/`

This is used for:

- individual scenario reports
- suite reports

---

## Scenarios

### `scenario_01_validLoginTest.py`

**Scenario name:** `Scenario 01 - Valid Login Test`

Purpose:

- open the configured application login page
- log in with valid credentials from config
- verify successful login
- take dashboard screenshot
- log out
- verify login page is visible again
- take login-page screenshot

Primary tools:

- Playwright MCP browser tools

Config used:

- `OPENAI_API_KEY`
- `MODEL_NAME`
- `BROWSER_URL`
- `BROWSER_USERNAME`
- `BROWSER_PASSWORD`

Expected screenshot targets:

- `reports/Screenshots/scenario_01_dashboard.png`
- `reports/Screenshots/scenario_01_login_page.png`

---

### `scenario_02_invalidLoginTest.py`

**Scenario name:** `Scenario 02 - Invalid Login Test`

Purpose:

- navigate to the configured login page
- attempt login with invalid credentials
- verify that a visible login error appears
- capture evidence screenshot

Primary tools:

- Playwright MCP browser tools

Config used:

- `OPENAI_API_KEY`
- `MODEL_NAME`
- `BROWSER_URL`

Expected screenshot target:

- `reports/Screenshots/scenario_02_invalid_login_error.png`

---

### `scenario_03_databaseTableDepartmentTest.py`

**Scenario name:** `Scenario_03 - MySQL Department Data Query`

Purpose:

- connect to MySQL database `bakery_hr`
- query the `departments` table
- display rows in a structured format
- validate that `Bakery`, `Sales`, and `Finance` exist

Primary tools:

- MySQL MCP tools

Config used:

- `OPENAI_API_KEY`
- `MODEL_NAME`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

---

### `scenario_04_databaseTableEmployeeTest.py`

**Scenario name:** `Scenario_04 - MySQL Employees Data Query`

Purpose:

- connect to MySQL database `bakery_hr`
- query the `employees` table
- display rows in a structured format
- validate that `Anita Rao`, `Peter Shaw`, and `Rahul Mehta` exist

Primary tools:

- MySQL MCP tools

Config used:

- `OPENAI_API_KEY`
- `MODEL_NAME`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

---

## Configuration

All runtime settings live in `config/config.properties`.

Example template:

```properties
# OpenAI
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o

# Jira
JIRA_URL=https://your-org.atlassian.net
JIRA_USERNAME=you@example.com
JIRA_API_TOKEN=...
JIRA_PROJECTS_FILTER=SCRUM

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=bakery_hr

# REST API
REST_BASE_URL=https://api.example.com

# Filesystem
FILESYSTEM_PATH=D:\path\to\AgenticAIAutoGen\Data\files

# Browser
BROWSER_URL=https://your-app-url.com/login
BROWSER_USERNAME=Admin
BROWSER_PASSWORD=admin123
PLAYWRIGHT_HEADLESS=false

# Optional path overrides
UV_PATH=
SITE_PACKAGES_PATH=
```

### Important configuration notes

- `PLAYWRIGHT_HEADLESS=false` is the central switch for headed vs headless Playwright MCP runs.
- `MODEL_NAME` is read by scenarios and passed directly into `OpenAIChatCompletionClient`.
- `UV_PATH` and `SITE_PACKAGES_PATH` are optional fallbacks; the framework first tries to resolve them from `.venv/` automatically.

> Do **not** commit real credentials or tokens to source control.

---

## Reports and Screenshots

### HTML reports

Generated HTML files are written to:

- `reports/result/`

Examples:

- `reports/result/Scenario_01_-_Valid_Login_Test_<timestamp>.html`
- `reports/result/suite_AgenticAI_Test_Suite_<timestamp>.html`

### Screenshots

Screenshots are stored under:

- `reports/Screenshots/`

Examples:

- `reports/Screenshots/scenario_01_dashboard.png`
- `reports/Screenshots/scenario_01_login_page.png`
- `reports/Screenshots/scenario_02_invalid_login_error.png`

### Relationship between report and screenshots

Scenario reports live in `reports/result/`, so image references inside HTML reports are rendered relative to that folder.

---

## Setup

### Prerequisites

Verified or implied by the current codebase:

- Python 3.10+
- Node.js with `npx`
- Chrome installed (Playwright MCP is configured with `--browser chrome`)
- Docker (only needed if you use the Jira workbench)
- MySQL server for database scenarios
- a virtual environment with `uv` available in `.venv`

### Install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Playwright/browser prerequisites

If Playwright browser dependencies are not already installed in your environment, install them before running UI scenarios.

```powershell
npx playwright install
```

---

## How to Run

### Run one scenario

```powershell
python .\scenarios\scenario_01_validLoginTest.py
python .\scenarios\scenario_02_invalidLoginTest.py
python .\scenarios\scenario_03_databaseTableDepartmentTest.py
python .\scenarios\scenario_04_databaseTableEmployeeTest.py
```

### Run the full suite

```powershell
python .\run_suite.py
```

Current suite behavior in `run_suite.py`:

- auto-discovers all files matching `scenarios/scenario*.py`
- executes them in alphabetical order
- writes individual reports plus one suite report
- opens the suite HTML report in the default browser at the end

---

## Preparing for GitHub Check-in

Before publishing this project, keep local secrets and generated artifacts out of source control.

### What is now safe by default

The repository is prepared with:

- `.gitignore` for:
  - `.venv/`
  - `__pycache__/`
  - `.idea/`
  - `memory.json`
  - `config/config.properties`
  - generated files under `reports/result/`
  - generated screenshots under `reports/Screenshots/`
- `config/config.properties.example` as the committed setup template
- placeholder values in `config/config.properties`
- `.gitkeep` files to preserve empty output folders in Git

### Local setup before running after clone

Copy the example config and fill in your real values locally:

```powershell
Copy-Item .\config\config.properties.example .\config\config.properties
```

Then edit `config/config.properties` and add your own credentials.

### Recommended first GitHub commit flow

```powershell
git init
git add .gitignore README.md requirements.txt run_suite.py .\framework .\libs .\scenarios .\config\config.properties.example .\config\__init__.py .\reports\result\.gitkeep .\reports\Screenshots\.gitkeep
git status
git commit -m "Prepare project for GitHub check-in"
```

### Important security note

Real credentials were previously present in local config during development. If any of those secrets were ever shared, backed up, or committed elsewhere, rotate them before publishing.

## Notes and Known Behavior

- The current `run_suite.py` implementation does **not** provide working CLI filters such as `--run` or `--skip`, even though commented example lines exist at the bottom of the file.
- UI scenarios rely on Playwright MCP tool execution through the LLM, so prompt size and model limits can affect runtime stability.
- `capture_agent_screenshot` is a helper for generating canonical screenshot paths; the actual image file is created only when `browser_take_screenshot(...)` is called.
- The framework currently includes reusable API, Excel, and Jira agent support even though the committed scenario suite mainly exercises browser and database flows.

---

## Core Concepts

### MCP Workbench

Each agent is attached to a workbench that exposes tool calls from an MCP server process. For example:

- browser tools from Playwright MCP
- query tools from MySQL MCP
- file tools from filesystem MCP

### `RoundRobinGroupChat`

Scenarios assemble one or more agents into a round-robin team. Messages are passed through the team until a configured termination condition is met.

### `TextMentionTermination`

Each scenario uses a token or keyword to indicate completion. When that token appears in an agent response, the group chat stops.

### `run_scenario_with_report(...)`

This helper centralizes the common scenario lifecycle:

- start reporter
- run team
- capture pass/fail
- save report
- close model client

That keeps scenario files small and consistent.
