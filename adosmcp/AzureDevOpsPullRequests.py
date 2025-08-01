import logging
from typing import List, Dict, Any, Optional
from azure.devops.connection import Connection
from azure.devops.v7_1.git.models import GitPullRequestSearchCriteria
from .decorators import azure_devops_error_handler

logging.basicConfig(level=logging.INFO)


class AzureDevOpsPullRequests:
    def __init__(self, connection: Connection):
        self.connection = connection
        try:
            self.git_client = self.connection.clients.get_git_client()
            logging.info("Successfully initialized pull requests client")
        except Exception as e:
            logging.error(f"Failed to initialize pull requests client: {str(e)}")
            raise

    @azure_devops_error_handler
    async def list_pull_requests(self, project: str, repository_id: str, 
                                status: str = "active", limit: int = 50) -> List[Dict[str, Any]]:
        """List pull requests in a repository"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
            
        # Ensure limit is within reasonable bounds
        limit = min(max(limit, 1), 200)
        
        # Map status to API enum values
        status_map = {
            "active": "active",
            "completed": "completed", 
            "abandoned": "abandoned",
            "all": "all"
        }
        api_status = status_map.get(status.lower(), "active")
        
        search_criteria = GitPullRequestSearchCriteria(
            status=api_status,
            target_ref_name=None,
            source_ref_name=None,
            creator_id=None,
            reviewer_id=None
        )
        
        pull_requests = self.git_client.get_pull_requests(
            repository_id=repository_id,
            project=project,
            search_criteria=search_criteria,
            max_comment_length=100,
            skip=0,
            top=limit
        )
        
        return [self._serialize_pull_request(pr) for pr in pull_requests]

    @azure_devops_error_handler
    async def get_pull_request(self, project: str, repository_id: str, pull_request_id: int) -> Dict[str, Any]:
        """Get details of a specific pull request"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
        if not pull_request_id or pull_request_id <= 0:
            raise ValueError("Valid pull request ID is required")
            
        pull_request = self.git_client.get_pull_request(
            repository_id=repository_id,
            project=project,
            pull_request_id=pull_request_id,
            max_comment_length=1000,
            include_commits=True,
            include_work_item_refs=True
        )
        
        return self._serialize_pull_request_detailed(pull_request)

    @azure_devops_error_handler
    async def create_pull_request(self, project: str, repository_id: str, 
                                 title: str, description: str,
                                 source_branch: str, target_branch: str,
                                 reviewers: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new pull request"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
        if not title:
            raise ValueError("Title is required")
        if not source_branch:
            raise ValueError("Source branch is required")
        if not target_branch:
            raise ValueError("Target branch is required")
            
        # Prepare source and target refs
        source_ref = f"refs/heads/{source_branch}" if not source_branch.startswith("refs/") else source_branch
        target_ref = f"refs/heads/{target_branch}" if not target_branch.startswith("refs/") else target_branch
        
        # Prepare reviewers if provided
        pr_reviewers = []
        if reviewers:
            for reviewer in reviewers:
                pr_reviewers.append({
                    "id": reviewer,
                    "displayName": reviewer,
                    "uniqueName": reviewer
                })
        
        # Create pull request object
        pr_data = {
            "sourceRefName": source_ref,
            "targetRefName": target_ref,
            "title": title,
            "description": description if description else "",
            "reviewers": pr_reviewers
        }
        
        pull_request = self.git_client.create_pull_request(
            git_pull_request_to_create=pr_data,
            repository_id=repository_id,
            project=project
        )
        
        return self._serialize_pull_request_detailed(pull_request)

    @azure_devops_error_handler
    async def get_pull_request_comments(self, project: str, repository_id: str, 
                                      pull_request_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get comments/threads for a pull request"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
        if not pull_request_id or pull_request_id <= 0:
            raise ValueError("Valid pull request ID is required")
            
        # Ensure limit is within reasonable bounds
        limit = min(max(limit, 1), 200)
        
        threads = self.git_client.get_threads(
            repository_id=repository_id,
            project=project,
            pull_request_id=pull_request_id,
            iteration=None,
            base_iteration=None
        )
        
        # Limit results
        limited_threads = threads[:limit] if threads else []
        
        return [self._serialize_thread(thread) for thread in limited_threads]

    @azure_devops_error_handler
    async def update_pull_request(self, project: str, repository_id: str, 
                                 pull_request_id: int, **fields) -> Dict[str, Any]:
        """Update a pull request (title, description, status, etc.)"""
        if not project:
            raise ValueError("Project name is required")
        if not repository_id:
            raise ValueError("Repository ID or name is required")
        if not pull_request_id or pull_request_id <= 0:
            raise ValueError("Valid pull request ID is required")
        if not fields:
            raise ValueError("At least one field to update is required")
            
        # Build update object with only provided fields
        update_data = {}
        
        if 'title' in fields and fields['title']:
            update_data['title'] = fields['title']
        if 'description' in fields and fields['description']:
            update_data['description'] = fields['description']
        if 'status' in fields and fields['status']:
            # Map friendly status names to API values
            status_map = {
                "active": "active",
                "completed": "completed",
                "abandoned": "abandoned"
            }
            update_data['status'] = status_map.get(fields['status'].lower(), fields['status'])
        
        pull_request = self.git_client.update_pull_request(
            git_pull_request_to_update=update_data,
            repository_id=repository_id,
            project=project,
            pull_request_id=pull_request_id
        )
        
        return self._serialize_pull_request_detailed(pull_request)

    def _serialize_pull_request(self, pr) -> Dict[str, Any]:
        """Convert GitPullRequest to dictionary (basic info)"""
        return {
            "pull_request_id": pr.pull_request_id,
            "title": pr.title,
            "description": pr.description,
            "status": pr.status,
            "creation_date": pr.creation_date.isoformat() if pr.creation_date else None,
            "source_ref_name": pr.source_ref_name,
            "target_ref_name": pr.target_ref_name,
            "created_by": {
                "display_name": pr.created_by.display_name if pr.created_by else None,
                "unique_name": pr.created_by.unique_name if pr.created_by else None,
                "id": pr.created_by.id if pr.created_by else None
            } if pr.created_by else None,
            "repository": {
                "id": pr.repository.id if pr.repository else None,
                "name": pr.repository.name if pr.repository else None
            } if pr.repository else None,
            "url": pr.url if hasattr(pr, 'url') else None,
            "is_draft": pr.is_draft if hasattr(pr, 'is_draft') else False
        }

    def _serialize_pull_request_detailed(self, pr) -> Dict[str, Any]:
        """Convert GitPullRequest to dictionary (detailed info)"""
        basic_info = self._serialize_pull_request(pr)
        
        # Add detailed information
        basic_info.update({
            "closed_date": pr.closed_date.isoformat() if hasattr(pr, 'closed_date') and pr.closed_date else None,
            "merge_status": pr.merge_status if hasattr(pr, 'merge_status') else None,
            "merge_id": pr.merge_id if hasattr(pr, 'merge_id') else None,
            "last_merge_source_commit": {
                "commit_id": pr.last_merge_source_commit.commit_id if hasattr(pr, 'last_merge_source_commit') and pr.last_merge_source_commit else None
            } if hasattr(pr, 'last_merge_source_commit') and pr.last_merge_source_commit else None,
            "last_merge_target_commit": {
                "commit_id": pr.last_merge_target_commit.commit_id if hasattr(pr, 'last_merge_target_commit') and pr.last_merge_target_commit else None
            } if hasattr(pr, 'last_merge_target_commit') and pr.last_merge_target_commit else None,
            "reviewers": [
                {
                    "display_name": reviewer.display_name if hasattr(reviewer, 'display_name') else None,
                    "unique_name": reviewer.unique_name if hasattr(reviewer, 'unique_name') else None,
                    "id": reviewer.id if hasattr(reviewer, 'id') else None,
                    "vote": reviewer.vote if hasattr(reviewer, 'vote') else 0,
                    "is_required": reviewer.is_required if hasattr(reviewer, 'is_required') else False
                }
                for reviewer in pr.reviewers
            ] if hasattr(pr, 'reviewers') and pr.reviewers else [],
            "work_item_refs": [
                {
                    "id": ref.id if hasattr(ref, 'id') else None,
                    "url": ref.url if hasattr(ref, 'url') else None
                }
                for ref in pr.work_item_refs
            ] if hasattr(pr, 'work_item_refs') and pr.work_item_refs else []
        })
        
        return basic_info

    def _serialize_thread(self, thread) -> Dict[str, Any]:
        """Convert GitPullRequestCommentThread to dictionary"""
        return {
            "id": thread.id,
            "status": thread.status if hasattr(thread, 'status') else None,
            "thread_context": {
                "file_path": thread.thread_context.file_path if hasattr(thread, 'thread_context') and thread.thread_context and hasattr(thread.thread_context, 'file_path') else None,
                "left_file_start": {
                    "line": thread.thread_context.left_file_start.line if hasattr(thread, 'thread_context') and thread.thread_context and hasattr(thread.thread_context, 'left_file_start') and thread.thread_context.left_file_start else None
                } if hasattr(thread, 'thread_context') and thread.thread_context and hasattr(thread.thread_context, 'left_file_start') else None,
                "right_file_start": {
                    "line": thread.thread_context.right_file_start.line if hasattr(thread, 'thread_context') and thread.thread_context and hasattr(thread.thread_context, 'right_file_start') and thread.thread_context.right_file_start else None
                } if hasattr(thread, 'thread_context') and thread.thread_context and hasattr(thread.thread_context, 'right_file_start') else None
            } if hasattr(thread, 'thread_context') and thread.thread_context else None,
            "comments": [
                {
                    "id": comment.id if hasattr(comment, 'id') else None,
                    "content": comment.content if hasattr(comment, 'content') else None,
                    "published_date": comment.published_date.isoformat() if hasattr(comment, 'published_date') and comment.published_date else None,
                    "last_updated_date": comment.last_updated_date.isoformat() if hasattr(comment, 'last_updated_date') and comment.last_updated_date else None,
                    "author": {
                        "display_name": comment.author.display_name if hasattr(comment, 'author') and comment.author and hasattr(comment.author, 'display_name') else None,
                        "unique_name": comment.author.unique_name if hasattr(comment, 'author') and comment.author and hasattr(comment.author, 'unique_name') else None,
                        "id": comment.author.id if hasattr(comment, 'author') and comment.author and hasattr(comment.author, 'id') else None
                    } if hasattr(comment, 'author') and comment.author else None,
                    "comment_type": comment.comment_type if hasattr(comment, 'comment_type') else None
                }
                for comment in thread.comments
            ] if hasattr(thread, 'comments') and thread.comments else [],
            "is_deleted": thread.is_deleted if hasattr(thread, 'is_deleted') else False,
            "last_updated_date": thread.last_updated_date.isoformat() if hasattr(thread, 'last_updated_date') and thread.last_updated_date else None,
            "published_date": thread.published_date.isoformat() if hasattr(thread, 'published_date') and thread.published_date else None
        }