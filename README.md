# Azure DevOps Server MCP

A Model Context Protocol (MCP) server for Azure DevOps Server/TFS that provides work item management and team project operations through Claude and other MCP-compatible clients.

## Features

- **Team Projects**: List projects, get project details, and manage teams
- **Work Items**: Create, read, update, and query work items with full field support
- **WIQL Support**: Execute custom Work Item Query Language queries
- **Environment-based Configuration**: Secure credential management through environment variables

## Prerequisites

- Installed Python 3.10 or higher

### Using uv (Recommended)

Install [uv](https://github.com/astral-sh/uv) for fast Python package management:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Ensure you have Python 3.10+ installed:

```bash
python --version  # Should be 3.10 or higher
python3 --version
```

Clone the repository

```bash
git clone <repository-url>
cd azure-devops-server-mcp
```

Install dependencies

```bash
pip install -e .
```

## Configuration

### Environment Variables

Set the following environment variables for your Azure DevOps Server:

```bash
export AZURE_DEVOPS_SERVER_URL="https://your-server.company.com/tfs"
export AZURE_DEVOPS_SERVER_TOKEN="your-personal-access-token"
export AZURE_DEVOPS_SERVER_COLLECTION="collection-name"
export AZURE_DEVOPS_SERVER_API_VERSION="7.1-preview.3"
```

### Personal Access Token

1. Go to your Azure DevOps Server web interface
2. Navigate to User Settings → Personal Access Tokens
3. Create a new token with the following scopes:
   - **Work Items**: Read & Write
   - **Project and Team**: Read

### Claude Desktop Configuration

Add the following to your Claude Desktop configuration file:

**Using uv:**

```json
{
  "mcpServers": {
    "azure-devops-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/azure-devops-server-mcp",
        "run", 
        "azure-devops-server-mcp"
      ],
      "env": {
        "AZURE_DEVOPS_SERVER_URL": "https://your-server.company.com/tfs",
        "AZURE_DEVOPS_SERVER_TOKEN": "your-personal-access-token",
        "AZURE_DEVOPS_SERVER_API_VERSION": "7.1-preview.3",
        "AZURE_DEVOPS_SERVER_COLLECTION": "collection-name"
      }
    }
  }
}
```

## Usage

Once configured with Claude Desktop, you can use natural language to interact with your Azure DevOps Server:

### Team Projects

- "List all team projects"
- "Get details for project 'MyProject'"
- "Show me teams in the 'Development' project"

### Work Items

- "List recent work items from project 'MyProject'"
- "Create a bug titled 'Login issue' in project 'WebApp'"
- "Update work item 1234 to set state to 'In Progress'"
- "Query all tasks assigned to john.doe@company.com in project 'MyProject'"

### Advanced Queries

- "Find all high priority bugs in 'MyProject' that are active"
- "Show me work items changed in the last week"

## Available Tools

### Team Project Tools

- `list_team_projects()`: Get all projects in the collection
- `get_team_project(project_id_or_name)`: Get specific project details
- `list_teams(project_id_or_name)`: List teams in a project

### Work Item Tools

- `list_work_items(project, query?, limit?)`: List work items with optional WIQL query
- `get_work_item(work_item_id)`: Get specific work item details
- `create_work_item(project, work_item_type, title, ...)`: Create new work item
- `update_work_item(work_item_id, ...)`: Update existing work item
- `query_work_items(project, filters...)`: Query with field filters
