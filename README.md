# Azure DevOps Server MCP

A Model Context Protocol (MCP) server for Azure DevOps **Server** (TFS). If you are looking for the Azure DevOps Services Cloud version, please see the official [azure-devops-mcp](https://github.com/microsoft/azure-devops-mcp) from Microsoft.

## Features

- **Git Repositories**: List repositories, browse files, get commit history, and manage branches
- **Pull Requests**: Create, read, update PRs, manage comments and reviews
- **Team Projects**: List projects, get project details, and manage teams
- **Work Items**: Create, read, update, and query work items with full field support
- **WIQL Support**: Execute custom Work Item Query Language queries

## Prerequisites

### Python 3.10+

Ensure you have Python 3.10+ installed:

```bash
python --version
python3 --version
```

### Using uv (Recommended)

Install [uv](https://github.com/astral-sh/uv) for fast Python package management:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Clone the repository

```bash
git clone https://github.com/Ravio1i/azure-devops-server-mcp
echo $PWD
```

## Configuration

### Personal Access Token

To interact with Azure DevOps Server, you need a Personal Access Token (PAT):

1. Go to your Azure DevOps Server web interface
2. Click on user top right corner -> Security → Personal Access Tokens
3. Create a new token with the following scopes:
   - **Work Items**: Read & Write
   - **Project and Team**: Read
   - **Code**: Read & Write (for Git repositories and Pull Requests)

### MCP Configuration

Add the following mcp Server e.g for Claude Code

- Edit your environment variables in `env`
- Adjust the path in the `args` section to point to your cloned repository

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

Once configured, you can use natural language to interact with your Azure DevOps Server:

### Git Repositories

- "List all repositories in project 'MyProject'"
- "Show me branches in repository 'MyRepo'"
- "Get the latest 10 commits from main branch in 'MyRepo'"
- "Show me the content of 'README.md' file from 'MyRepo'"
- "List files in the 'src' folder of 'MyRepo'"

### Pull Requests

- "List active pull requests in repository 'MyRepo'"
- "Create a PR from 'feature-branch' to 'main' with title 'Add new feature'"
- "Show me details of pull request #42 in 'MyRepo'"
- "Get comments on pull request #42"
- "Update PR #42 status to completed"

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

### Git Repository Tools

- `list_repositories(project)`: Get all repositories in a project
- `get_repository(project, repository_id)`: Get specific repository details
- `list_branches(project, repository_id, limit?)`: List branches in repository
- `get_commits(project, repository_id, branch?, limit?)`: Get commit history
- `get_file_content(project, repository_id, path, branch?)`: Get file content
- `list_repository_items(project, repository_id, path?, branch?, limit?)`: List files/folders

### Pull Request Tools

- `list_pull_requests(project, repository_id, status?, limit?)`: List pull requests
- `get_pull_request(project, repository_id, pull_request_id)`: Get PR details
- `create_pull_request(project, repository_id, title, description, source_branch, target_branch, reviewers?)`: Create new PR
- `get_pull_request_comments(project, repository_id, pull_request_id, limit?)`: Get PR comments
- `update_pull_request(project, repository_id, pull_request_id, ...)`: Update PR

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
