import logging
from typing import List, Dict, Any, Optional
from azure.devops.connection import Connection
from azure.devops.v7_1.work_item_tracking.models import Wiql, WorkItem, JsonPatchOperation
from .decorators import azure_devops_error_handler, rate_limit, request_size_limit

logging.basicConfig(level=logging.INFO)


class AzureDevOpsWorkItems:
    def __init__(self, connection: Connection):
        self.connection = connection
        try:
            self.wit_client = self.connection.clients.get_work_item_tracking_client()
            logging.info("Successfully initialized work item tracking client")
        except Exception as e:
            logging.error(f"Failed to initialize work item tracking client: {str(e)}")
            raise

    @rate_limit(requests_per_minute=30)
    @azure_devops_error_handler
    async def list_work_items(self, project: str, query: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List work items from a project with pagination support"""
        if not project:
            raise ValueError("Project name is required")
            
        if not query:
            # Dynamic query that works with any project
            query = f"SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], [System.WorkItemType] FROM WorkItems WHERE [System.TeamProject] = '{project}'"
        
        logging.info("Executing WIQL query for work items")
        wiql = Wiql(query=query)
        result = self.wit_client.query_by_wiql(wiql)
        
        if not result.work_items:
            logging.info(f"No work items found for project {project}")
            return []
        
        # Get work item IDs from the query result, limited to prevent hanging
        work_item_ids = [wi.id for wi in result.work_items[:limit]]
        logging.info(f"Found {len(work_item_ids)} work items to process")
        
        # Process work items in small batches to avoid URL length limits
        batch_size = 20  # Smaller batch size to ensure stability
        work_items = []
        
        for i in range(0, len(work_item_ids), batch_size):
            batch_ids = work_item_ids[i:i + batch_size]
            logging.info(f"Processing batch {i//batch_size + 1}: {len(batch_ids)} items")
            try:
                batch_items = self.wit_client.get_work_items(ids=batch_ids, expand="Fields")
                work_items.extend(batch_items)
            except Exception as batch_error:
                logging.error(f"Error processing batch {i//batch_size + 1}: {batch_error}")
                # Continue with next batch instead of failing completely
                continue
        
        return [self._serialize_work_item(wi) for wi in work_items]

    @rate_limit(requests_per_minute=60)
    @azure_devops_error_handler
    async def get_work_item(self, work_item_id: int) -> Dict[str, Any]:
        """Get a specific work item by ID"""
        if not work_item_id or work_item_id <= 0:
            raise ValueError("Valid work item ID is required")
            
        work_item = self.wit_client.get_work_item(id=work_item_id, expand="All")
        return self._serialize_work_item(work_item)

    @request_size_limit(max_size_mb=5)
    @rate_limit(requests_per_minute=20)
    @azure_devops_error_handler
    async def create_work_item(self, project: str, work_item_type: str, title: str, 
                             description: Optional[str] = None, **fields) -> Dict[str, Any]:
        """Create a new work item"""
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

    @request_size_limit(max_size_mb=5)
    @rate_limit(requests_per_minute=20)
    @azure_devops_error_handler
    async def update_work_item(self, work_item_id: int, **fields) -> Dict[str, Any]:
        """Update an existing work item"""
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

    def _serialize_work_item(self, work_item: WorkItem) -> Dict[str, Any]:
        """Convert WorkItem to dictionary with essential fields only"""
        try:
            # Extract key fields safely
            fields = work_item.fields if work_item.fields else {}
            
            # Get essential field values
            title = fields.get("System.Title", "")
            state = fields.get("System.State", "")
            work_item_type = fields.get("System.WorkItemType", "")
            assigned_to = fields.get("System.AssignedTo", {})
            description = fields.get("System.Description", "")
            
            # Handle assigned_to which can be a complex object
            assigned_to_name = ""
            if assigned_to:
                if isinstance(assigned_to, dict):
                    assigned_to_name = assigned_to.get("displayName", assigned_to.get("uniqueName", ""))
                else:
                    assigned_to_name = str(assigned_to)
            
            return {
                "id": work_item.id,
                "title": title,
                "description": description,
                "state": state,
                "work_item_type": work_item_type,
                "assigned_to": assigned_to_name,
                "url": work_item.url,
                "rev": work_item.rev
            }
        except Exception as e:
            logging.error(f"Error serializing work item {work_item.id}: {e}")
            # Return minimal info if serialization fails
            return {
                "id": work_item.id,
                "title": "Error loading work item",
                "description": description,
                "state": "Unknown",
                "work_item_type": "Unknown",
                "assigned_to": "",
                "url": work_item.url if work_item.url else "",
                "rev": work_item.rev if work_item.rev else 0
            }
