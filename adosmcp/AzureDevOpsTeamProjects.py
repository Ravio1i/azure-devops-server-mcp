import logging
from typing import List, Dict, Any
from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsServiceError

logging.basicConfig(level=logging.INFO)


class AzureDevOpsTeamProjects:
    def __init__(self, connection: Connection):
        self.connection = connection
        try:
            self.core_client = self.connection.clients.get_core_client()
            logging.info("Successfully initialized team projects client")
        except Exception as e:
            logging.error(f"Failed to initialize team projects client: {str(e)}")
            raise

    async def list_team_projects(self) -> List[Dict[str, Any]]:
        """List all team projects in the Azure DevOps Server/TFS collection"""
        try:
            projects = self.core_client.get_projects()
            
            return [self._serialize_project(project) for project in projects]
        except AzureDevOpsServiceError as e:
            logging.error(f"Azure DevOps API error in list_team_projects: {e}")
            raise Exception(f"Failed to list team projects: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in list_team_projects: {e}")
            raise Exception(f"Unexpected error listing team projects: {str(e)}")

    async def get_team_project(self, project_id_or_name: str) -> Dict[str, Any]:
        """Get details of a specific team project"""
        try:
            if not project_id_or_name:
                raise ValueError("Project ID or name is required")
                
            project = self.core_client.get_project(project_id_or_name)
            return self._serialize_project(project)
        except AzureDevOpsServiceError as e:
            logging.error(f"Azure DevOps API error in get_team_project: {e}")
            raise Exception(f"Failed to get team project '{project_id_or_name}': {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in get_team_project: {e}")
            raise Exception(f"Unexpected error getting team project '{project_id_or_name}': {str(e)}")

    async def list_teams(self, project_id_or_name: str) -> List[Dict[str, Any]]:
        """List all teams in a specific project"""
        try:
            if not project_id_or_name:
                raise ValueError("Project ID or name is required")
                
            teams = self.core_client.get_teams(project_id_or_name)
            
            return [self._serialize_team(team) for team in teams]
        except AzureDevOpsServiceError as e:
            logging.error(f"Azure DevOps API error in list_teams: {e}")
            raise Exception(f"Failed to list teams for project '{project_id_or_name}': {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in list_teams: {e}")
            raise Exception(f"Unexpected error listing teams for project '{project_id_or_name}': {str(e)}")

    def _serialize_project(self, project) -> Dict[str, Any]:
        """Convert TeamProject to dictionary"""
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description if hasattr(project, 'description') else None,
            "url": project.url if hasattr(project, 'url') else None,
            "state": project.state if hasattr(project, 'state') else None,
            "revision": project.revision if hasattr(project, 'revision') else None,
            "visibility": project.visibility if hasattr(project, 'visibility') else None,
            "last_update_time": project.last_update_time.isoformat() if hasattr(project, 'last_update_time') and project.last_update_time else None
        }

    def _serialize_team(self, team) -> Dict[str, Any]:
        """Convert WebApiTeam to dictionary"""
        return {
            "id": team.id,
            "name": team.name,
            "url": team.url if hasattr(team, 'url') else None,
            "description": team.description if hasattr(team, 'description') else None,
            "identity_url": team.identity_url if hasattr(team, 'identity_url') else None
        }