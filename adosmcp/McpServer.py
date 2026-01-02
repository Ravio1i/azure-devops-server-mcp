import logging
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from .AzureDevOpsServerClient import AzureDevOpsServerClient

logging.basicConfig(level=logging.INFO)


class McpServer:
    def __init__(self):
        self.mcp = FastMCP("azure-devops-server")
        self.ado_client = AzureDevOpsServerClient()
        self._register_tools()
    
    def _register_tools(self):
        # Test Suites and Test Points tool (REST API)
        import requests

        @self.mcp.tool()
        async def get_testsuites_testpoints(project: str, plan_id: str = None, plan_name: str = None, outcome: str = None) -> Dict[str, Any]:
            """Get all test suites and test points for a test plan in a team project using REST API
            Args:
                project: Team project name
                plan_id: Test plan ID
                plan_name: Test plan name
                outcome: Filter testpoints by outcome (Failed, Passed, Unspecified)
            Returns:
                Dictionary with suites and their test points
            """
            import os
            planet = os.environ.get('AZURE_DEVOPS_SERVER_URL', 'jupiter.tfs.siemens.net').replace('https://','').replace('/tfs','')
            collection = os.environ.get('AZURE_DEVOPS_SERVER_COLLECTION', 'IPS')
            pat = os.environ.get('AZURE_DEVOPS_SERVER_TOKEN')
            if not pat:
                raise ValueError("Personal Access Token (PAT) is required. Set AZURE_DEVOPS_SERVER_TOKEN.")
            def get_test_plans(planet, collection, project, pat):
                url = f"https://{planet}/tfs/{collection}/{project}/_apis/test/plans?includePlanDetails=true&api-version=4.0"
                auth = requests.auth.HTTPBasicAuth('', pat)
                response = requests.get(url, auth=auth)
                response.raise_for_status()
                return response.json().get('value', [])
            def get_test_suites(planet, collection, project, plan_id, pat):
                url = f"https://{planet}/tfs/{collection}/{project}/_apis/test/plans/{plan_id}/suites?api-version=4.0"
                auth = requests.auth.HTTPBasicAuth('', pat)
                response = requests.get(url, auth=auth)
                response.raise_for_status()
                return response.json().get('value', [])
            def get_test_points(planet, collection, project, plan_id, suite_id, pat):
                url = f"https://{planet}/tfs/{collection}/{project}/_apis/test/plans/{plan_id}/suites/{suite_id}/points?api-version=4.0"
                auth = requests.auth.HTTPBasicAuth('', pat)
                response = requests.get(url, auth=auth)
                response.raise_for_status()
                return response.json().get('value', [])
            # If plan_name is given, look up its ID
            if plan_name:
                plans = get_test_plans(planet, collection, project, pat)
                match = [p for p in plans if p.get('name', '').lower() == plan_name.lower()]
                if not match:
                    return {"error": f"Test plan with name '{plan_name}' not found in project '{project}'."}
                plan_id = match[0].get('id')
            if not plan_id:
                return {"error": "Test plan ID or name must be provided."}
            suites = get_test_suites(planet, collection, project, plan_id, pat)
            allowed_outcomes = {"Failed", "Passed", "Unspecified"}
            filter_outcome = outcome
            result = {}
            for suite in suites:
                suite_id = suite.get('id')
                suite_name = suite.get('name')
                points = get_test_points(planet, collection, project, plan_id, suite_id, pat)
                # Filter points by outcome
                if filter_outcome:
                    filtered_points = [point for point in points if point.get('outcome', 'Unknown') == filter_outcome]
                else:
                    filtered_points = [point for point in points if point.get('outcome', 'Unknown') in allowed_outcomes]
                if filtered_points:
                    result[suite_name] = [{
                        "testPoint": point.get('testCase', {}).get('name', 'Unknown'),
                        "outcome": point.get('outcome', 'Unknown')
                    } for point in filtered_points]
            if not result:
                return {"message": "There are not any testsuites that fulfill the outcome condition."}
            return result
        # Test Plans tool
        from azure.devops.connection import Connection
        from msrest.authentication import BasicAuthentication
        from datetime import datetime, timedelta

        @self.mcp.tool()
        async def list_test_plans(project: str, active: bool = False, lastdays: int = None, latest: bool = False) -> List[Dict[str, Any]]:
            """List test plans for a specific Azure DevOps Server team project using SDK only
            Args:
                project: Team project name
                active: Show only active test plans
                lastdays: Show test plans updated in the last N days
                latest: Show only the latest test plan
            Returns:
                List of test plans
            """
            import os
            planet = os.environ.get('AZURE_DEVOPS_SERVER_URL', 'jupiter.tfs.siemens.net').replace('https://','').replace('/tfs','')
            collection = os.environ.get('AZURE_DEVOPS_SERVER_COLLECTION', 'IPS')
            pat = os.environ.get('AZURE_DEVOPS_SERVER_TOKEN')
            if not pat:
                raise ValueError("Personal Access Token (PAT) is required. Set AZURE_DEVOPS_SERVER_TOKEN.")
            org_url = f"https://{planet}/tfs/{collection}"
            credentials = BasicAuthentication('', pat)
            connection = Connection(base_url=org_url, creds=credentials)
            try:
                test_client = connection.clients.get_test_plan_client()
                plans = test_client.get_test_plans(project)
                plans = [
                    {
                        "id": plan.id,
                        "name": plan.name,
                        "state": plan.state,
                        "updatedDate": getattr(plan, 'updated_date', None)
                    }
                    for plan in plans
                ]
            except Exception as e:
                import logging
                logging.error(f"SDK error: {e}")
                return []
            # Filtering
            for plan in plans:
                if plan.get('updatedDate'):
                    try:
                        plan['updatedDate_dt'] = datetime.strptime(plan['updatedDate'][:19], "%Y-%m-%dT%H:%M:%S")
                    except Exception:
                        plan['updatedDate_dt'] = None
                else:
                    plan['updatedDate_dt'] = None
            filtered_plans = plans
            if active:
                filtered_plans = [p for p in filtered_plans if str(p.get('state','')).lower() == 'active']
            if lastdays:
                cutoff = datetime.now() - timedelta(days=lastdays)
                filtered_plans = [p for p in filtered_plans if p['updatedDate_dt'] and p['updatedDate_dt'] >= cutoff]
            if latest and filtered_plans:
                filtered_plans = [max(filtered_plans, key=lambda p: p['updatedDate_dt'] or datetime.min)]
            return filtered_plans
        # Team Projects tools
        @self.mcp.tool()
        async def list_team_projects() -> List[Dict[str, Any]]:
            """List all team projects in the Azure DevOps Server/TFS collection
            
            Returns:
                List of team projects with their metadata
            """
            return await self.ado_client.team_projects.list_team_projects()

        @self.mcp.tool()
        async def get_team_project(project_id_or_name: str) -> Dict[str, Any]:
            """Get details of a specific team project
            
            Args:
                project_id_or_name: The ID or name of the project to retrieve
            
            Returns:
                Team project details
            """
            return await self.ado_client.team_projects.get_team_project(project_id_or_name)

        @self.mcp.tool()
        async def list_teams(project_id_or_name: str) -> List[Dict[str, Any]]:
            """List all teams in a specific project
            
            Args:
                project_id_or_name: The ID or name of the project
            
            Returns:
                List of teams in the project
            """
            return await self.ado_client.team_projects.list_teams(project_id_or_name)

        # Work Items tools
        @self.mcp.tool()
        async def list_work_items(project: str, query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
            """List work items from an Azure DevOps project
            
            Args:
                project: The name of the Azure DevOps project
                query: Optional WIQL query string. If not provided, lists recent work items in the project
                limit: Maximum number of work items to return (default: 50, max recommended: 200)
            
            Returns:
                List of work items with their fields and metadata
            """
            # Ensure limit is within reasonable bounds to prevent resource exhaustion
            limit = min(max(limit, 1), 100)
            return await self.ado_client.work_items.list_work_items(project, query if query else None, limit)

        @self.mcp.tool()
        async def get_work_item(work_item_id: int) -> Dict[str, Any]:
            """Get a specific work item by its ID
            
            Args:
                work_item_id: The ID of the work item to retrieve
            
            Returns:
                Work item details including all fields and relations
            """
            return await self.ado_client.work_items.get_work_item(work_item_id)

        @self.mcp.tool()
        async def create_work_item(project: str, work_item_type: str, title: str, 
                                 description: str = "", assigned_to: str = "", 
                                 state: str = "", priority: str = "") -> Dict[str, Any]:
            """Create a new work item in Azure DevOps
            
            Args:
                project: The name of the Azure DevOps project
                work_item_type: Type of work item (e.g., 'Bug', 'Task', 'User Story')
                title: The title of the work item
                description: Optional description
                assigned_to: Optional assignee email/username
                state: Optional initial state
                priority: Optional priority level
            
            Returns:
                Created work item details
            """
            fields = {}
            if assigned_to:
                fields["System.AssignedTo"] = assigned_to
            if state:
                fields["System.State"] = state
            if priority:
                fields["Microsoft.VSTS.Common.Priority"] = priority
                
            return await self.ado_client.work_items.create_work_item(
                project, work_item_type, title, description if description else None, **fields
            )

        @self.mcp.tool()
        async def update_work_item(work_item_id: int, title: str = "", description: str = "",
                                 assigned_to: str = "", state: str = "", priority: str = "") -> Dict[str, Any]:
            """Update an existing work item
            
            Args:
                work_item_id: The ID of the work item to update
                title: New title (optional)
                description: New description (optional)
                assigned_to: New assignee email/username (optional)
                state: New state (optional)
                priority: New priority level (optional)
            
            Returns:
                Updated work item details
            """
            fields = {}
            if title:
                fields["System.Title"] = title
            if description:
                fields["System.Description"] = description
            if assigned_to:
                fields["System.AssignedTo"] = assigned_to
            if state:
                fields["System.State"] = state
            if priority:
                fields["Microsoft.VSTS.Common.Priority"] = priority
                
            return await self.ado_client.work_items.update_work_item(work_item_id, **fields)

        @self.mcp.tool()
        async def query_work_items(project: str, work_item_type: str = "", 
                                 state: str = "", assigned_to: str = "", limit: int = 50) -> List[Dict[str, Any]]:
            """Query work items with filters
            
            Args:
                project: The name of the Azure DevOps project
                work_item_type: Filter by work item type (optional)
                state: Filter by state (optional)
                assigned_to: Filter by assignee (optional)
                limit: Maximum number of work items to return (default: 50, max recommended: 200)
            
            Returns:
                List of work items matching the criteria
            """
            # Ensure limit is within reasonable bounds first to prevent resource exhaustion
            limit = min(max(limit, 1), 100)
            
            conditions = [f"[System.TeamProject] = '{project}'"]
            
            if work_item_type:
                conditions.append(f"[System.WorkItemType] = '{work_item_type}'")
            if state:
                conditions.append(f"[System.State] = '{state}'")
            if assigned_to:
                conditions.append(f"[System.AssignedTo] = '{assigned_to}'")
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], [System.WorkItemType], [System.ChangedDate] FROM WorkItems WHERE {where_clause} ORDER BY [System.ChangedDate] DESC"
            return await self.ado_client.work_items.list_work_items(project, query, limit)

        # Git Repository tools
        @self.mcp.tool()
        async def list_repositories(project: str) -> List[Dict[str, Any]]:
            """List all Git repositories in a project
            
            Args:
                project: The name of the Azure DevOps project
            
            Returns:
                List of repositories with their metadata
            """
            return await self.ado_client.git_repositories.list_repositories(project)

        @self.mcp.tool()
        async def get_repository(project: str, repository_id: str) -> Dict[str, Any]:
            """Get details of a specific repository
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
            
            Returns:
                Repository details
            """
            return await self.ado_client.git_repositories.get_repository(project, repository_id)

        @self.mcp.tool()
        async def list_branches(project: str, repository_id: str, limit: int = 50) -> List[Dict[str, Any]]:
            """List branches in a repository
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
                limit: Maximum number of branches to return (default: 50, max: 200)
            
            Returns:
                List of branches
            """
            limit = min(max(limit, 1), 100)
            return await self.ado_client.git_repositories.list_branches(project, repository_id, limit)

        @self.mcp.tool()
        async def get_commits(project: str, repository_id: str, branch: str = "main", limit: int = 50) -> List[Dict[str, Any]]:
            """Get commit history for a branch
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
                branch: Branch name (default: main)
                limit: Maximum number of commits to return (default: 50, max: 200)
            
            Returns:
                List of commits
            """
            limit = min(max(limit, 1), 100)
            return await self.ado_client.git_repositories.get_commits(project, repository_id, branch, limit)

        @self.mcp.tool()
        async def get_file_content(project: str, repository_id: str, path: str, branch: str = "main") -> Dict[str, Any]:
            """Get content of a file from repository
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
                path: Path to the file
                branch: Branch name (default: main)
            
            Returns:
                File content and metadata
            """
            return await self.ado_client.git_repositories.get_file_content(project, repository_id, path, branch)

        @self.mcp.tool()
        async def list_repository_items(project: str, repository_id: str, path: str = "/", 
                                       branch: str = "main", limit: int = 100) -> List[Dict[str, Any]]:
            """List files and folders in a repository path
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
                path: Path to list (default: /)
                branch: Branch name (default: main)
                limit: Maximum number of items to return (default: 100, max: 500)
            
            Returns:
                List of files and folders
            """
            limit = min(max(limit, 1), 200)  # Reduced from 500 for security
            return await self.ado_client.git_repositories.list_items(project, repository_id, path, branch, limit)

        # Pull Request tools
        @self.mcp.tool()
        async def list_pull_requests(project: str, repository_id: str, status: str = "active", 
                                   limit: int = 50) -> List[Dict[str, Any]]:
            """List pull requests in a repository
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
                status: PR status filter (active, completed, abandoned, all)
                limit: Maximum number of PRs to return (default: 50, max: 200)
            
            Returns:
                List of pull requests
            """
            limit = min(max(limit, 1), 100)
            return await self.ado_client.pull_requests.list_pull_requests(project, repository_id, status, limit)

        @self.mcp.tool()
        async def get_pull_request(project: str, repository_id: str, pull_request_id: int) -> Dict[str, Any]:
            """Get details of a specific pull request
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
                pull_request_id: The ID of the pull request
            
            Returns:
                Pull request details including reviewers and work items
            """
            return await self.ado_client.pull_requests.get_pull_request(project, repository_id, pull_request_id)

        @self.mcp.tool()
        async def create_pull_request(project: str, repository_id: str, title: str, description: str,
                                    source_branch: str, target_branch: str, 
                                    reviewers: str = "") -> Dict[str, Any]:
            """Create a new pull request
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
                title: Title of the pull request
                description: Description of the pull request
                source_branch: Source branch name
                target_branch: Target branch name
                reviewers: Comma-separated list of reviewer emails/usernames (optional)
            
            Returns:
                Created pull request details
            """
            reviewer_list = [r.strip() for r in reviewers.split(",")] if reviewers else None
            return await self.ado_client.pull_requests.create_pull_request(
                project, repository_id, title, description, source_branch, target_branch, reviewer_list
            )

        @self.mcp.tool()
        async def get_pull_request_comments(project: str, repository_id: str, pull_request_id: int,
                                          limit: int = 50) -> List[Dict[str, Any]]:
            """Get comments/threads for a pull request
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
                pull_request_id: The ID of the pull request
                limit: Maximum number of comment threads to return (default: 50, max: 200)
            
            Returns:
                List of comment threads
            """
            limit = min(max(limit, 1), 100)
            return await self.ado_client.pull_requests.get_pull_request_comments(project, repository_id, pull_request_id, limit)

        @self.mcp.tool()
        async def update_pull_request(project: str, repository_id: str, pull_request_id: int,
                                    title: str = "", description: str = "", status: str = "") -> Dict[str, Any]:
            """Update a pull request
            
            Args:
                project: The name of the Azure DevOps project
                repository_id: The ID or name of the repository
                pull_request_id: The ID of the pull request
                title: New title (optional)
                description: New description (optional)
                status: New status - active, completed, abandoned (optional)
            
            Returns:
                Updated pull request details
            """
            fields = {}
            if title:
                fields["title"] = title
            if description:
                fields["description"] = description
            if status:
                fields["status"] = status
                
            return await self.ado_client.pull_requests.update_pull_request(project, repository_id, pull_request_id, **fields)
    
    def run(self):
        self.mcp.run()