import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_1.work_item_tracking.models import Wiql, WorkItem, JsonPatchOperation
from azure.devops.exceptions import AzureDevOpsServiceError

logging.basicConfig(level=logging.INFO)


class AzureDevOpsServerMCP:
    def __init__(self):
        self.server_url = os.getenv("AZURE_DEVOPS_SERVER_URL")
        self.token = os.getenv("AZURE_DEVOPS_SERVER_TOKEN")
        self.collection = os.getenv("AZURE_DEVOPS_SERVER_COLLECTION", "")  # Default to ALM collection
        self.api_version = os.getenv("AZURE_DEVOPS_SERVER_API_VERSION", "7.1-preview.3")
        
        if not self.server_url or not self.token:
            raise ValueError("AZURE_DEVOPS_SERVER_URL and AZURE_DEVOPS_SERVER_TOKEN must be set")
        
        # Construct the full URL with collection if provided and not already included
        if self.collection and not self.server_url.endswith(self.collection):
            if not self.server_url.endswith('/'):
                self.server_url += '/'
            self.server_url += self.collection
        
        logging.info(f"Using TFS URL: {self.server_url}")
        
        # Use standard PAT format for Azure DevOps Server - "pat" as username with token as password
        credentials = BasicAuthentication("pat", self.token)
        self.connection = Connection(base_url=self.server_url, creds=credentials)
        
        try:
            self.wit_client = self.connection.clients.get_work_item_tracking_client()
            logging.info(f"Successfully connected to Azure DevOps Server at {self.server_url}")
        except Exception as e:
            logging.error(f"Failed to connect to Azure DevOps Server: {str(e)}")
            raise

    async def list_work_items(self, project: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List work items from a project"""
        try:
            if not project:
                raise ValueError("Project name is required")
                
            if not query:
                query = f"SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo] FROM WorkItems WHERE [System.TeamProject] = '{project}'"
            
            wiql = Wiql(query=query)
            result = self.wit_client.query_by_wiql(wiql)
            
            if not result.work_items:
                return []
            
            work_item_ids = [wi.id for wi in result.work_items]
            work_items = self.wit_client.get_work_items(ids=work_item_ids, expand="All")
            
            return [self._serialize_work_item(wi) for wi in work_items]
        except AzureDevOpsServiceError as e:
            logging.error(f"Azure DevOps API error in list_work_items: {e}")
            raise Exception(f"Failed to list work items: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in list_work_items: {e}")
            raise Exception(f"Unexpected error listing work items: {str(e)}")

    async def get_work_item(self, work_item_id: int) -> Dict[str, Any]:
        """Get a specific work item by ID"""
        try:
            if not work_item_id or work_item_id <= 0:
                raise ValueError("Valid work item ID is required")
                
            work_item = self.wit_client.get_work_item(id=work_item_id, expand="All")
            return self._serialize_work_item(work_item)
        except AzureDevOpsServiceError as e:
            logging.error(f"Azure DevOps API error in get_work_item: {e}")
            raise Exception(f"Failed to get work item {work_item_id}: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in get_work_item: {e}")
            raise Exception(f"Unexpected error getting work item {work_item_id}: {str(e)}")

    async def create_work_item(self, project: str, work_item_type: str, title: str, 
                             description: Optional[str] = None, **fields) -> Dict[str, Any]:
        """Create a new work item"""
        try:
            if not project:
                raise ValueError("Project name is required")
            if not work_item_type:
                raise ValueError("Work item type is required")
            if not title:
                raise ValueError("Title is required")
                
            document = []
            
            document.append(JsonPatchOperation(
                op="add",
                path="/fields/System.Title",
                value=title
            ))
            
            if description:
                document.append(JsonPatchOperation(
                    op="add",
                    path="/fields/System.Description",
                    value=description
                ))
            
            for field_name, field_value in fields.items():
                if field_value:  # Only add non-empty values
                    document.append(JsonPatchOperation(
                        op="add",
                        path=f"/fields/{field_name}",
                        value=field_value
                    ))
            
            work_item = self.wit_client.create_work_item(
                document=document,
                project=project,
                type=work_item_type
            )
            
            return self._serialize_work_item(work_item)
        except AzureDevOpsServiceError as e:
            logging.error(f"Azure DevOps API error in create_work_item: {e}")
            raise Exception(f"Failed to create work item: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in create_work_item: {e}")
            raise Exception(f"Unexpected error creating work item: {str(e)}")

    async def update_work_item(self, work_item_id: int, **fields) -> Dict[str, Any]:
        """Update an existing work item"""
        try:
            if not work_item_id or work_item_id <= 0:
                raise ValueError("Valid work item ID is required")
            if not fields:
                raise ValueError("At least one field to update is required")
                
            document = []
            
            for field_name, field_value in fields.items():
                if field_value:  # Only update non-empty values
                    document.append(JsonPatchOperation(
                        op="replace",
                        path=f"/fields/{field_name}",
                        value=field_value
                    ))
            
            if not document:
                raise ValueError("No valid fields provided for update")
                
            work_item = self.wit_client.update_work_item(
                document=document,
                id=work_item_id
            )
            
            return self._serialize_work_item(work_item)
        except AzureDevOpsServiceError as e:
            logging.error(f"Azure DevOps API error in update_work_item: {e}")
            raise Exception(f"Failed to update work item {work_item_id}: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in update_work_item: {e}")
            raise Exception(f"Unexpected error updating work item {work_item_id}: {str(e)}")

    def _serialize_work_item(self, work_item: WorkItem) -> Dict[str, Any]:
        """Convert WorkItem to dictionary"""
        return {
            "id": work_item.id,
            "url": work_item.url,
            "fields": work_item.fields if work_item.fields else {},
            "relations": work_item.relations if work_item.relations else [],
            "rev": work_item.rev
        }


class AzureDevOpsMCPServer:
    def __init__(self):
        self.mcp = FastMCP("azure-devops-server")
        self.ado_client = AzureDevOpsServerMCP()
        self._register_tools()
    
    def _register_tools(self):
        @self.mcp.tool()
        async def list_work_items(project: str, query: str = "") -> List[Dict[str, Any]]:
            """List work items from an Azure DevOps project
            
            Args:
                project: The name of the Azure DevOps project
                query: Optional WIQL query string. If not provided, lists all work items in the project
            
            Returns:
                List of work items with their fields and metadata
            """
            return await self.ado_client.list_work_items(project, query if query else None)

        @self.mcp.tool()
        async def get_work_item(work_item_id: int) -> Dict[str, Any]:
            """Get a specific work item by its ID
            
            Args:
                work_item_id: The ID of the work item to retrieve
            
            Returns:
                Work item details including all fields and relations
            """
            return await self.ado_client.get_work_item(work_item_id)

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
                
            return await self.ado_client.create_work_item(
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
                
            return await self.ado_client.update_work_item(work_item_id, **fields)

        @self.mcp.tool()
        async def query_work_items(project: str, work_item_type: str = "", 
                                 state: str = "", assigned_to: str = "") -> List[Dict[str, Any]]:
            """Query work items with filters
            
            Args:
                project: The name of the Azure DevOps project
                work_item_type: Filter by work item type (optional)
                state: Filter by state (optional)
                assigned_to: Filter by assignee (optional)
            
            Returns:
                List of work items matching the criteria
            """
            conditions = [f"[System.TeamProject] = '{project}'"]
            
            if work_item_type:
                conditions.append(f"[System.WorkItemType] = '{work_item_type}'")
            if state:
                conditions.append(f"[System.State] = '{state}'")
            if assigned_to:
                conditions.append(f"[System.AssignedTo] = '{assigned_to}'")
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], [System.WorkItemType] FROM WorkItems WHERE {where_clause}"
            
            return await self.ado_client.list_work_items(project, query)
    
    def run(self):
        self.mcp.run()


def main():
    server = AzureDevOpsMCPServer()
    server.run()


if __name__ == "__main__":
    main()
