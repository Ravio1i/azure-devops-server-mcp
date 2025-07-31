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
            # Ensure limit is within reasonable bounds
            limit = min(max(limit, 1), 200)
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
            # Ensure limit is within reasonable bounds first
            limit = min(max(limit, 1), 200)
            
            conditions = [f"[System.TeamProject] = '{project}'"]
            
            if work_item_type:
                conditions.append(f"[System.WorkItemType] = '{work_item_type}'")
            if state:
                conditions.append(f"[System.State] = '{state}'")
            if assigned_to:
                conditions.append(f"[System.AssignedTo] = '{assigned_to}'")
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT TOP {limit} [System.Id], [System.Title], [System.State], [System.AssignedTo], [System.WorkItemType], [System.ChangedDate] FROM WorkItems WHERE {where_clause} ORDER BY [System.ChangedDate] DESC"
            return await self.ado_client.work_items.list_work_items(project, query, limit)
    
    def run(self):
        self.mcp.run()