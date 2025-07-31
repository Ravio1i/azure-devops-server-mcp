import os
import logging
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from .AzureDevOpsWorkItems import AzureDevOpsWorkItems
from .AzureDevOpsTeamProjects import AzureDevOpsTeamProjects

logging.basicConfig(level=logging.INFO)


class AzureDevOpsServerClient:
    def __init__(self):
        self.server_url = os.getenv("AZURE_DEVOPS_SERVER_URL")
        self.token = os.getenv("AZURE_DEVOPS_SERVER_TOKEN")
        self.collection = os.getenv("AZURE_DEVOPS_SERVER_COLLECTION", "")
        self.api_version = os.getenv("AZURE_DEVOPS_SERVER_API_VERSION", "7.1-preview.3")
        
        if not self.server_url or not self.token:
            raise ValueError("AZURE_DEVOPS_SERVER_URL and AZURE_DEVOPS_SERVER_TOKEN must be set")
        
        # Construct the full URL with collection if provided and not already included
        if self.collection and not self.server_url.endswith(self.collection):
            if not self.server_url.endswith('/'):
                self.server_url += '/'
            self.server_url += self.collection
        
        logging.info(f"Using TFS URL: {self.server_url}")
        
        # Use standard PAT format for Azure DevOps Server
        credentials = BasicAuthentication("pat", self.token)
        self.connection = Connection(base_url=self.server_url, creds=credentials)
        
        # Initialize specialized clients
        self.work_items = AzureDevOpsWorkItems(self.connection)
        self.team_projects = AzureDevOpsTeamProjects(self.connection)
        
        logging.info(f"Successfully connected to Azure DevOps Server at {self.server_url}")