import logging
from typing import List, Dict, Any
from azure.devops.connection import Connection
from .decorators import azure_devops_error_handler

logging.basicConfig(level=logging.INFO)


class AzureDevOpsGitRepositories:
    def __init__(self, connection: Connection):
        self.connection = connection
        try:
            self.git_client = self.connection.clients.get_git_client()
            logging.info("Successfully initialized git client")
        except Exception as e:
            logging.error(f"Failed to initialize git client: {str(e)}")
            raise

    @azure_devops_error_handler
    async def list_repositories(self, project: str) -> List[Dict[str, Any]]:
        """List all Git repositories in a project"""
        if not project:
            raise ValueError("Project name is required")
            
        repositories = self.git_client.get_repositories(project)
        
        return [self._serialize_repository(repo) for repo in repositories]

    @azure_devops_error_handler
    async def get_repository(self, project: str, repository_id: str) -> Dict[str, Any]:
        """Get details of a specific repository"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
            
        repository = self.git_client.get_repository(project, repository_id)
        return self._serialize_repository(repository)

    @azure_devops_error_handler
    async def list_branches(self, project: str, repository_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List branches in a repository"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
            
        # Ensure limit is within reasonable bounds
        limit = min(max(limit, 1), 200)
        
        refs = self.git_client.get_refs(
            repository_id=repository_id,
            project=project,
            filter="heads/"
        )
        
        # Limit results
        limited_refs = refs[:limit] if refs else []
        
        return [self._serialize_branch(ref) for ref in limited_refs]

    @azure_devops_error_handler
    async def get_commits(self, project: str, repository_id: str, branch: str = "main", limit: int = 50) -> List[Dict[str, Any]]:
        """Get commit history for a branch"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
            
        # Ensure limit is within reasonable bounds
        limit = min(max(limit, 1), 200)
        
        commits = self.git_client.get_commits(
            repository_id=repository_id,
            project=project,
            search_criteria={
                'itemVersion': {
                    'version': branch,
                    'versionType': 'branch'
                },
                '$top': limit
            }
        )
        
        return [self._serialize_commit(commit) for commit in commits]

    @azure_devops_error_handler
    async def get_file_content(self, project: str, repository_id: str, path: str, branch: str = "main") -> Dict[str, Any]:
        """Get content of a file from repository"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
        if not path:
            raise ValueError("File path is required")
            
        item = self.git_client.get_item(
            repository_id=repository_id,
            project=project,
            path=path,
            version_descriptor={
                'version': branch,
                'versionType': 'branch'
            }
        )
        
        return self._serialize_file_item(item)

    @azure_devops_error_handler
    async def list_items(self, project: str, repository_id: str, path: str = "/", branch: str = "main", limit: int = 100) -> List[Dict[str, Any]]:
        """List files and folders in a repository path"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
            
        # Ensure limit is within reasonable bounds
        limit = min(max(limit, 1), 500)
        
        items = self.git_client.get_items(
            repository_id=repository_id,
            project=project,
            scope_path=path,
            version_descriptor={
                'version': branch,
                'versionType': 'branch'
            },
            recursion_level='OneLevel'
        )
        
        # Limit results and exclude the root path item itself
        filtered_items = [item for item in items if item.path != path][:limit]
        
        return [self._serialize_item(item) for item in filtered_items]

    def _serialize_repository(self, repo) -> Dict[str, Any]:
        """Convert GitRepository to dictionary"""
        return {
            "id": repo.id,
            "name": repo.name,
            "url": repo.url if hasattr(repo, 'url') else None,
            "ssh_url": repo.ssh_url if hasattr(repo, 'ssh_url') else None,
            "web_url": repo.web_url if hasattr(repo, 'web_url') else None,
            "default_branch": repo.default_branch if hasattr(repo, 'default_branch') else None,
            "size": repo.size if hasattr(repo, 'size') else None,
            "is_fork": repo.is_fork if hasattr(repo, 'is_fork') else None,
            "project": {
                "id": repo.project.id if hasattr(repo, 'project') and repo.project else None,
                "name": repo.project.name if hasattr(repo, 'project') and repo.project else None
            } if hasattr(repo, 'project') and repo.project else None
        }

    def _serialize_branch(self, ref) -> Dict[str, Any]:
        """Convert GitRef to dictionary for branch"""
        branch_name = ref.name.replace("refs/heads/", "") if ref.name.startswith("refs/heads/") else ref.name
        return {
            "name": branch_name,
            "object_id": ref.object_id,
            "url": ref.url if hasattr(ref, 'url') else None,
            "is_locked": ref.is_locked if hasattr(ref, 'is_locked') else False
        }

    def _serialize_commit(self, commit) -> Dict[str, Any]:
        """Convert GitCommitRef to dictionary"""
        return {
            "commit_id": getattr(commit, 'commit_id', None),
            "author": {
                "name": getattr(commit.author, 'name', None) if hasattr(commit, 'author') and commit.author else None,
                "email": getattr(commit.author, 'email', None) if hasattr(commit, 'author') and commit.author else None,
                "date": commit.author.date.isoformat() if hasattr(commit, 'author') and commit.author and hasattr(commit.author, 'date') and commit.author.date else None
            } if hasattr(commit, 'author') and commit.author else None,
            "committer": {
                "name": getattr(commit.committer, 'name', None) if hasattr(commit, 'committer') and commit.committer else None,
                "email": getattr(commit.committer, 'email', None) if hasattr(commit, 'committer') and commit.committer else None,
                "date": commit.committer.date.isoformat() if hasattr(commit, 'committer') and commit.committer and hasattr(commit.committer, 'date') and commit.committer.date else None
            } if hasattr(commit, 'committer') and commit.committer else None,
            "comment": getattr(commit, 'comment', None),
            "url": getattr(commit, 'url', None),
            "remote_url": getattr(commit, 'remote_url', None)
        }

    def _serialize_file_item(self, item) -> Dict[str, Any]:
        """Convert GitItem to dictionary for file content"""
        return {
            "object_id": item.object_id,
            "path": item.path,
            "content": item.content if hasattr(item, 'content') else None,
            "content_metadata": {
                "encoding": item.content_metadata.encoding if hasattr(item, 'content_metadata') and item.content_metadata else None,
                "content_type": item.content_metadata.content_type if hasattr(item, 'content_metadata') and item.content_metadata else None,
                "file_name": item.content_metadata.file_name if hasattr(item, 'content_metadata') and item.content_metadata else None,
                "is_binary": item.content_metadata.is_binary if hasattr(item, 'content_metadata') and item.content_metadata else False,
                "is_image": item.content_metadata.is_image if hasattr(item, 'content_metadata') and item.content_metadata else False,
                "vs_link": item.content_metadata.vs_link if hasattr(item, 'content_metadata') and item.content_metadata else None
            } if hasattr(item, 'content_metadata') and item.content_metadata else None,
            "url": item.url if hasattr(item, 'url') else None,
            "is_folder": item.is_folder if hasattr(item, 'is_folder') else False,
            "size": item.size if hasattr(item, 'size') else None
        }

    def _serialize_item(self, item) -> Dict[str, Any]:
        """Convert GitItem to dictionary for directory listing"""
        return {
            "object_id": item.object_id,
            "path": item.path,
            "is_folder": item.is_folder if hasattr(item, 'is_folder') else False,
            "size": item.size if hasattr(item, 'size') else None,
            "url": item.url if hasattr(item, 'url') else None,
            "git_object_type": item.git_object_type if hasattr(item, 'git_object_type') else None
        }