import base64
import logging
import os
from typing import Dict, Any, List, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JiraTools:

    def __init__(self):
        self.JIRA_API_TOKEN = None
        self.JIRA_USERNAME = None
        self.JIRA_BASE_URL = None

    def set_credential(self):
        self.JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
        self.JIRA_USERNAME = os.getenv("JIRA_USERNAME")
        self.JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

    def _get_auth_header(self) -> str:
        """
        Generate Basic Auth header for Jira API
        """
        credentials = f"{self.JIRA_USERNAME}:{self.JIRA_API_TOKEN}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"

    def _make_jira_request(self, endpoint: str, params: Dict[str, Any] = None, method: str = "GET",
                           data: Dict[str, Any] = None,
                           check_jira_health: bool = True) -> Dict[str, Any]:
        """
        Make HTTP request to Jira API
        """
        logger.info(f"Making jira request to {endpoint}")
        self.set_credential()
        url = f"{self.JIRA_BASE_URL}{endpoint}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": self._get_auth_header()
        }

        if check_jira_health:
            check_if_server_healthy = self._check_jira_health()

            if check_if_server_healthy.get('status', 'unhealthy') == 'unhealthy':
                return check_if_server_healthy

        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise Exception(f"Unsupported HTTP method: {method}")

            response.raise_for_status()

            # Handle empty responses (e.g., for DELETE operations)
            if response.status_code == 204 or not response.content:
                return {"success": True, "message": "Operation completed successfully"}

            return response.json()
        except Exception as e:
            logger.error("Exception while calling Jira api" + str(e))
            return {"error": True, "message": str(e)}

    def jira_get_issue(self, issue_key: str, expand: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a specific Jira issue by its key.
        Args:
            issue_key: The Jira issue key (e.g., "PROJ-123")
            expand: Optional comma-separated list of fields to expand (e.g., "comments,attachments")
        Returns:
            Dictionary containing the issue details
        """
        logger.info(f"Getting Jira issue {issue_key}")
        endpoint = f"/issue/{issue_key}"
        params = {}
        if expand:
            params["expand"] = expand
        return self._make_jira_request(endpoint, params=params)

    def jira_search(self, jql: str, max_results: int = 50, start_at: int = 0, fields: Optional[List[str]] = None) -> \
            Dict[str, Any]:
        """
        Search for Jira issues using JQL (Jira Query Language).
        Args:
            jql: JQL query string (e.g., "project = PROJ AND status = 'To Do'")
            max_results: Maximum number of results to return (default: 50)
            start_at: Starting index for pagination (default: 0)
            fields: Optional list of fields to include in results
        Returns:
            Dictionary containing search results
        """
        endpoint = "/search"
        data = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at
        }
        if fields:
            data["fields"] = fields
        return self._make_jira_request(endpoint, method="POST", data=data)

    def jira_create_story_with_description_and_comment(self, project_key: str, summary: str, description: str = "",
                                                       initial_comment: str = "",
                                                       assignee: Optional[str] = None,
                                                       labels: Optional[List[str]] = None,
                                                       custom_fields: Optional[Dict[str, Any]] = None,
                                                       comment_visibility: Optional[Dict[str, str]] = None) -> Dict[
        str, Any]:
        """
        Create a new Jira story with description and add an initial comment in a single operation.
        This reduces the number of API calls needed for MCP server agentic operations.

        Args:
            project_key: The project key (e.g., "PROJ")
            summary: Brief description of the story
            description: Detailed description (supports Atlassian Document Format)
            initial_comment: Initial comment to add after story creation
            assignee: Username or account ID of the assignee
            labels: List of labels to add to the story
            custom_fields: Dictionary of custom field values
            comment_visibility: Optional visibility settings for the comment
        Returns:
            Dictionary containing the created story details and comment status
        """
        logger.info(
            f"Creating Jira story with comment for {project_key}: {summary} and {description} and {initial_comment}")

        # Step 1: Create the story
        story_result = self.jira_create_issue(
            project_key=project_key,
            issue_type="Story",  # Fixed to Story type
            summary=summary,
            description=description,
            assignee=assignee,
            labels=labels,
            custom_fields=custom_fields
        )

        # Check if story creation failed
        if "error" in story_result:
            logger.error(f"Failed to create story: {story_result.get('message', 'Unknown error')}")
            return {
                "error": True,
                "message": f"Story creation failed: {story_result.get('message', 'Unknown error')}",
                "story_result": story_result
            }

        # Extract the created issue key
        issue_key = story_result.get("key")
        if not issue_key:
            logger.error("No issue key returned from story creation")
            return {
                "error": True,
                "message": "Story created but no issue key returned",
                "story_result": story_result
            }

        logger.info(f"Story created successfully: {issue_key}")

        # Step 2: Add initial comment if provided
        comment_result = None
        if initial_comment.strip():
            logger.info(f"Adding initial comment to story {issue_key}")
            comment_result = self.jira_add_comment(
                issue_key=issue_key,
                comment=initial_comment,
                visibility=comment_visibility
            )

            if "error" in comment_result:
                logger.warning(
                    f"Failed to add comment to {issue_key}: {comment_result.get('message', 'Unknown error')}")
                # Don't fail the entire operation if comment fails
                comment_result["warning"] = True

        # Step 3: Return combined results
        result = {
            "success": True,
            "issue_key": issue_key,
            "story_url": f"{self.JIRA_BASE_URL.rstrip('/')}/browse/{issue_key}",
            "story_result": story_result,
            "message": f"Story {issue_key} created successfully"
        }

        if comment_result:
            if "error" in comment_result:
                result[
                    "comment_warning"] = f"Story created but comment failed: {comment_result.get('message', 'Unknown error')}"
                result["comment_result"] = comment_result
            else:
                result["comment_result"] = comment_result
                result["message"] += " with initial comment"

        logger.info(f"Story creation with comment completed for {issue_key}")
        return result

    def jira_create_stories_bulk(self, project_key: str, stories_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple Jira stories in bulk.
        This function creates stories sequentially and returns results for all operations.

        Args:
            project_key: The project key for all stories (e.g., "PROJ")
            stories_data: List of dictionaries, each containing story data.
                         Each dict should have at least 'summary' key.
                         Optional keys: 'description', 'assignee', 'labels', 'custom_fields',
                                       'initial_comment', 'comment_visibility'
        Returns:
            Dictionary containing:
            - 'success_count': Number of successfully created stories
            - 'error_count': Number of failed story creations
            - 'results': List of results for each story creation
            - 'successful_stories': List of successfully created stories with their keys
            - 'failed_stories': List of failed stories with error details
        """
        logger.info(f"Creating {len(stories_data)} Jira stories in bulk for project {project_key}")

        if not stories_data or not isinstance(stories_data, list):
            return {"error": True, "message": "stories_data must be a non-empty list"}

        if not project_key or not isinstance(project_key, str):
            return {"error": True, "message": "project_key must be a valid string"}

        results = []
        successful_stories = []
        failed_stories = []
        success_count = 0
        error_count = 0

        for i, story_data in enumerate(stories_data):
            try:
                # Validate required fields
                if not isinstance(story_data, dict) or 'summary' not in story_data:
                    error_result = {
                        "index": i,
                        "error": True,
                        "message": "Each story must be a dictionary with 'summary' key"
                    }
                    results.append(error_result)
                    failed_stories.append(error_result)
                    error_count += 1
                    continue

                # Extract story parameters with defaults
                summary = story_data['summary']
                description = story_data.get('description', '')
                assignee = story_data.get('assignee')
                labels = story_data.get('labels')
                custom_fields = story_data.get('custom_fields')
                initial_comment = story_data.get('initial_comment', '')
                comment_visibility = story_data.get('comment_visibility')

                logger.info(f"Creating story {i + 1}/{len(stories_data)}: {summary}")

                # Check if we need to create with comment or just the story
                if initial_comment.strip():
                    # Use the combined create and comment function
                    result = self.jira_create_story_with_description_and_comment(
                        project_key=project_key,
                        summary=summary,
                        description=description,
                        initial_comment=initial_comment,
                        assignee=assignee,
                        labels=labels,
                        custom_fields=custom_fields,
                        comment_visibility=comment_visibility
                    )
                else:
                    # Use regular create function
                    result = self.jira_create_issue(
                        project_key=project_key,
                        issue_type="Story",
                        summary=summary,
                        description=description,
                        assignee=assignee,
                        labels=labels,
                        custom_fields=custom_fields
                    )

                # Add index for tracking
                result['index'] = i
                results.append(result)

                if result.get('error'):
                    failed_stories.append({
                        "index": i,
                        "story_data": story_data,
                        "error": result.get('message', 'Unknown error')
                    })
                    error_count += 1
                else:
                    # Extract story key from result
                    story_key = result.get('issue_key') or result.get('key')
                    story_url = result.get('story_url',
                                           f"{self.JIRA_BASE_URL.rstrip('/')}/browse/{story_key}" if story_key else None)

                    successful_stories.append({
                        "index": i,
                        "issue_key": story_key,
                        "story_url": story_url,
                        "summary": summary,
                        "has_comment": bool(initial_comment.strip())
                    })
                    success_count += 1

            except Exception as e:
                error_result = {
                    "index": i,
                    "error": True,
                    "message": f"Exception occurred: {str(e)}",
                    "story_data": story_data
                }
                results.append(error_result)
                failed_stories.append(error_result)
                error_count += 1
                logger.error(f"Exception creating story {i + 1}: {str(e)}")

        summary = {
            "project_key": project_key,
            "success_count": success_count,
            "error_count": error_count,
            "total_count": len(stories_data),
            "results": results,
            "successful_stories": successful_stories,
            "failed_stories": failed_stories
        }

        logger.info(
            f"Bulk story creation completed for {project_key}: {success_count} successful, {error_count} failed")
        return summary

    def jira_create_issue(self, project_key: str, issue_type: str, summary: str, description: str = "",
                          assignee: Optional[str] = None,
                          labels: Optional[List[str]] = None, custom_fields: Optional[Dict[str, Any]] = None) -> Dict[
        str, Any]:
        """
        Create a new Jira issue with description.
        Args:
            project_key: The project key (e.g., "PROJ")
            issue_type: Issue type name (e.g., "Bug", "Task", "Story")
            summary: Brief description of the issue
            description: Detailed description (supports Atlassian Document Format)
            assignee: Username or account ID of the assignee
            labels: List of labels to add to the issue
            custom_fields: Dictionary of custom field values
        Returns:
            Dictionary containing the created issue details
        """
        logger.info(f"Creating Jira issue for {project_key} and {summary}")
        endpoint = "/issue"

        # Build issue data
        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "issuetype": {"name": issue_type},
                "summary": summary
            }
        }

        if description:
            # Use Atlassian Document Format for description
            issue_data["fields"]["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description
                            }
                        ]
                    }
                ]
            }

        # if priority:
        #     issue_data["fields"]["priority"] = {"name": priority}

        if assignee:
            issue_data["fields"]["assignee"] = {"accountId": assignee}

        if labels:
            issue_data["fields"]["labels"] = labels

        if custom_fields:
            issue_data["fields"].update(custom_fields)

        return self._make_jira_request(endpoint, method="POST", data=issue_data)

    def jira_update_issue(self, issue_key: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing Jira issue.
        Args:
            issue_key: The Jira issue key (e.g., "PROJ-123")
            update_data: Dictionary containing fields to update
        Returns:
            Dictionary containing the result of the update operation
        """
        logger.info(f"Updating jira issue {issue_key} with {str(update_data)}")
        endpoint = f"/issue/{issue_key}"

        # Wrap update data in the required format
        formatted_data = {"fields": update_data}

        return self._make_jira_request(endpoint, method="PUT", data=formatted_data)

    def jira_transition_issue(self, issue_key: str, transition_id: str, comment: Optional[str] = None,
                              fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transition a Jira issue to a different status.
        Args:
            issue_key: The Jira issue key (e.g., "PROJ-123")
            transition_id: ID of the transition to perform
            comment: Optional comment to add during transition
            fields: Optional fields to update during transition
        Returns:
            Dictionary containing the result of the transition
        """
        endpoint = f"/issue/{issue_key}/transitions"

        transition_data = {
            "transition": {"id": transition_id}
        }

        if comment:
            transition_data["update"] = {
                "comment": [
                    {
                        "add": {
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": comment
                                            }
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                ]
            }

        if fields:
            transition_data["fields"] = fields

        return self._make_jira_request(endpoint, method="POST", data=transition_data)

    def jira_add_comment(self, issue_key: str, comment: str, visibility: Optional[Dict[str, str]] = None) -> Dict[
        str, Any]:
        """
        Add a comment to a Jira issue.
        Args:
            issue_key: The Jira issue key (e.g., "PROJ-123")
            comment: The comment text to add
            visibility: Optional visibility settings (e.g., {"type": "role", "value": "Administrators"})
        Returns:
            Dictionary containing the created comment details
        """
        logger.info(f"Adding comment to {issue_key} with {comment}")
        endpoint = f"/issue/{issue_key}/comment"

        comment_data = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment
                            }
                        ]
                    }
                ]
            }
        }

        if visibility:
            comment_data["visibility"] = visibility

        return self._make_jira_request(endpoint, method="POST", data=comment_data)

    def get_jira_transitions(self, issue_key: str) -> Dict[str, Any]:
        """
        Get available transitions for a Jira issue.
        Args:
            issue_key: The Jira issue key (e.g., "PROJ-123")
        Returns:
            Dictionary containing available transitions
        """
        endpoint = f"/issue/{issue_key}/transitions"
        return self._make_jira_request(endpoint)

    def _check_jira_health(self) -> Dict[str, Any]:
        """
        Check if the Jira API is reachable and credentials are valid.
        Returns:
            Dictionary containing health status
        """
        try:
            logger.info(f"Checking Jira API is reachable")
            result = self._make_jira_request("/myself", check_jira_health=False)
            if "accountId" in result:
                return {"status": "healthy", "user": result.get("displayName", "Unknown"), "details": result}
            return {"status": "unhealthy", "details": result}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
