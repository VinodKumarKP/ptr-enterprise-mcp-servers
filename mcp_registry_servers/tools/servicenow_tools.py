import logging
import os
from typing import Dict, Any, List

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceNowTools:

    def __init__(self):
        self.SERVICENOW_PASSWORD = None
        self.SERVICENOW_USER = None
        self.SERVICENOW_BASE_URL = None

    def set_credential(self):
        self.SERVICENOW_BASE_URL = os.getenv('SERVICENOW_BASE_URL')
        self.SERVICENOW_USER = os.getenv("SERVICENOW_USER")
        self.SERVICENOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD")

    def _make_servicenow_request(self, endpoint: str, params: Dict[str, str] = None, method: str = "GET",
                                 data: Dict[str, Any] = None,
                                 check_servicenow_health: bool = True) -> Dict[str, Any]:
        """
        Make HTTP request to ServiceNow API
        """
        logger.info(f"Making ServiceNow request to {endpoint}")
        self.set_credential()
        url = f"{self.SERVICENOW_BASE_URL}{endpoint}"
        auth = (self.SERVICENOW_USER, self.SERVICENOW_PASSWORD)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        if check_servicenow_health:
            check_if_server_healthy = self._check_servicenow_health()

            if check_if_server_healthy.get('status', 'unhealthy') == 'unhealthy':
                return check_if_server_healthy

        try:
            if method == "GET":
                response = requests.get(url, params=params, auth=auth, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, auth=auth, headers=headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, auth=auth, headers=headers, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, json=data, auth=auth, headers=headers, timeout=30)
            else:
                raise Exception(f"Unsupported HTTP method: {method}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Exception while calling ServiceNow api" + str(e))
            return {"error": True, "message": str(e)}

    def get_servicenow_incidents(self, query: str = "active=true") -> Dict[str, Any]:
        """
        Fetch incidents from ServiceNow.
        Args:
            query: ServiceNow query string (default: active incidents)
        Returns:
            Dictionary containing incidents
        """
        logger.info(f"Getting ServiceNow Incidents using {query}")
        endpoint = f"/table/incident"
        params = {"sysparm_query": query}
        return self._make_servicenow_request(endpoint, params=params)

    def create_servicenow_incident(self, short_description: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new incident in ServiceNow.
        Args:
            short_description: Short description for the incident
            description: Detailed description
        Returns:
            Dictionary containing the created incident
        """
        logger.info(f"Creating ServiceNow incident with {short_description} and {description}")
        endpoint = f"/table/incident"
        data = {"short_description": short_description, "description": description}
        return self._make_servicenow_request(endpoint, method="POST", data=data)

    def update_servicenow_incident(self, incident_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing incident in ServiceNow.
        Args:
            incident_id: The sys_id of the incident to update
            update_data: Dictionary containing fields to update (e.g., state, priority, assigned_to, etc.)
        Returns:
            Dictionary containing the updated incident
        """
        logger.info(f"Updating ServiceNow incident {incident_id}")
        endpoint = f"/table/incident/{incident_id}"
        return self._make_servicenow_request(endpoint, method="PUT", data=update_data)

    def create_and_update_servicenow_incident(self, short_description: str, description: str = "",
                                              update_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new incident and immediately update it with additional data.
        This is useful when you need to create an incident and then add fields that can only be set after creation,
        or when you want to ensure the incident is created before applying complex updates.
        This reduces the number of tool calls needed for MCP server operations.

        Args:
            short_description: Short description for the new incident (required)
            description: Detailed description for the new incident
            update_data: Dictionary containing fields to update after creation (e.g., assignments, custom fields, etc.)
        Returns:
            Dictionary containing:
            - 'create_result': Result from the incident creation
            - 'update_result': Result from the incident update (if update_data provided)
            - 'final_incident': The final incident data after both operations
            - 'sys_id': The sys_id of the created incident
            - 'incident_number': The incident number assigned by ServiceNow
        """
        logger.info(f"Creating and updating ServiceNow incident: {short_description}")

        # Step 1: Create the incident
        logger.info("Step 1: Creating new incident")
        create_endpoint = "/table/incident"
        create_data = {"short_description": short_description, "description": description}

        create_result = self._make_servicenow_request(create_endpoint, method="POST", data=create_data)

        if create_result.get('error'):
            logger.error(f"Failed to create incident: {create_result.get('message')}")
            return {
                "error": True,
                "message": f"Failed to create incident: {create_result.get('message')}",
                "create_result": create_result,
                "update_result": None,
                "final_incident": None,
                "sys_id": None,
                "incident_number": None
            }

        # Extract incident details from creation result
        created_incident = create_result.get('result', {})
        incident_sys_id = created_incident.get('sys_id')
        incident_number = created_incident.get('number')

        if not incident_sys_id:
            logger.error("Failed to get sys_id from created incident")
            return {
                "error": True,
                "message": "Failed to get sys_id from created incident",
                "create_result": create_result,
                "update_result": None,
                "final_incident": None,
                "sys_id": None,
                "incident_number": incident_number
            }

        logger.info(f"Successfully created incident {incident_number} with sys_id: {incident_sys_id}")

        # Step 2: Update the incident if update_data is provided
        update_result = None
        final_incident = created_incident

        if update_data and isinstance(update_data, dict):
            logger.info(f"Step 2: Updating incident {incident_sys_id} with additional data")
            update_endpoint = f"/table/incident/{incident_sys_id}"

            update_result = self._make_servicenow_request(update_endpoint, method="PUT", data=update_data)

            if update_result.get('error'):
                logger.error(f"Failed to update incident {incident_sys_id}: {update_result.get('message')}")
                return {
                    "error": True,
                    "message": f"Incident created successfully but update failed: {update_result.get('message')}",
                    "create_result": create_result,
                    "update_result": update_result,
                    "final_incident": created_incident,  # Return the created incident even if update failed
                    "sys_id": incident_sys_id,
                    "incident_number": incident_number
                }
            else:
                final_incident = update_result.get('result', created_incident)
                logger.info(f"Successfully updated incident {incident_sys_id}")
        else:
            logger.info("No update data provided, skipping update step")

        return {
            "error": False,
            "message": f"Successfully created and updated incident {incident_number}",
            "create_result": create_result,
            "update_result": update_result,
            "final_incident": final_incident,
            "sys_id": incident_sys_id,
            "incident_number": incident_number
        }

    def create_servicenow_incidents_bulk(self, incidents_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple incidents in ServiceNow in bulk with optional comments and updates.
        This function uses create_and_update_servicenow_incident for each incident creation.
        This reduces the number of tool calls needed for MCP server operations.

        Args:
            incidents_data: List of dictionaries, each containing incident data.
                          Each dict should have at least 'short_description' key.
                          Required keys: 'short_description'
                          Optional keys: 'description', 'initial_comment', 'update_data', 'priority', 'urgency', etc.

                          Special handling:
                          - 'initial_comment': Will be added as work_notes after incident creation
                          - 'update_data': Dictionary of additional fields to update after creation
                          - Other fields (priority, urgency, etc.) will be included in update_data automatically
        Returns:
            Dictionary containing:
            - 'success_count': Number of successfully created incidents
            - 'error_count': Number of failed incident creations
            - 'results': List of results for each incident creation and update
            - 'successful_incidents': List of successfully created incidents with their sys_ids
            - 'failed_incidents': List of failed incidents with error details
        """
        logger.info(f"Creating {len(incidents_data)} ServiceNow incidents in bulk with comments and updates")

        if not incidents_data or not isinstance(incidents_data, list):
            return {"error": True, "message": "incidents_data must be a non-empty list"}

        results = []
        successful_incidents = []
        failed_incidents = []
        success_count = 0
        error_count = 0

        for i, incident_data in enumerate(incidents_data):
            try:
                # Validate required fields
                if not isinstance(incident_data, dict) or 'short_description' not in incident_data:
                    error_result = {
                        "index": i,
                        "error": True,
                        "message": "Each incident must be a dictionary with 'short_description' key"
                    }
                    results.append(error_result)
                    failed_incidents.append(error_result)
                    error_count += 1
                    continue

                # Extract core incident data
                short_description = incident_data['short_description']
                description = incident_data.get('description', '')
                initial_comment = incident_data.get('initial_comment', '')

                # Prepare update_data by combining explicit update_data with other fields
                update_data = incident_data.get('update_data', {}).copy() if incident_data.get('update_data') else {}

                # Add other fields to update_data (excluding the core creation fields and special fields)
                excluded_fields = {'short_description', 'description', 'initial_comment', 'update_data'}
                for key, value in incident_data.items():
                    if key not in excluded_fields:
                        update_data[key] = value

                # Add initial comment as work_notes if provided
                if initial_comment.strip():
                    # If there are existing work_notes in update_data, append to them
                    existing_notes = update_data.get('work_notes', '')
                    if existing_notes:
                        update_data['work_notes'] = f"{existing_notes}\n\nInitial Comment: {initial_comment}"
                    else:
                        update_data['work_notes'] = f"Initial Comment: {initial_comment}"

                logger.info(f"Creating and updating incident {i + 1}/{len(incidents_data)}: {short_description}")

                # Use create_and_update_servicenow_incident function
                result = self.create_and_update_servicenow_incident(
                    short_description=short_description,
                    description=description,
                    update_data=update_data if update_data else None
                )

                # Add index for tracking
                result['index'] = i
                results.append(result)

                if result.get('error'):
                    failed_incidents.append({
                        "index": i,
                        "incident_data": incident_data,
                        "error": result.get('message', 'Unknown error')
                    })
                    error_count += 1
                else:
                    # Extract incident details from the final result
                    final_incident = result.get('final_incident', {})
                    sys_id = result.get('sys_id')
                    incident_number = result.get('incident_number')

                    successful_incidents.append({
                        "index": i,
                        "sys_id": sys_id,
                        "incident_number": incident_number,
                        "short_description": short_description,
                        "has_comment": bool(initial_comment.strip()),
                        "has_updates": bool(update_data),
                        "create_success": not result.get('create_result', {}).get('error', False),
                        "update_success": not result.get('update_result', {}).get('error', False) if result.get(
                            'update_result') else True
                    })
                    success_count += 1

            except Exception as e:
                error_result = {
                    "index": i,
                    "error": True,
                    "message": f"Exception occurred: {str(e)}",
                    "incident_data": incident_data
                }
                results.append(error_result)
                failed_incidents.append(error_result)
                error_count += 1
                logger.error(f"Exception creating incident {i + 1}: {str(e)}")

        summary = {
            "success_count": success_count,
            "error_count": error_count,
            "total_count": len(incidents_data),
            "results": results,
            "successful_incidents": successful_incidents,
            "failed_incidents": failed_incidents
        }

        logger.info(
            f"Bulk incident creation with comments and updates completed: {success_count} successful, {error_count} failed")
        return summary

    def get_servicenow_incident_by_id(self, incident_id: str) -> Dict[str, Any]:
        """
        Get a specific incident from ServiceNow by its sys_id.
        Args:
            incident_id: The sys_id of the incident to retrieve
        Returns:
            Dictionary containing the incident details
        """
        logger.info(f"Getting ServiceNow incident by id {incident_id}")
        endpoint = f"/table/incident/{incident_id}"
        return self._make_servicenow_request(endpoint)

    def servicenow_incident_add_comment(self, incident_id: str, comment: str, comment_type: str = "work_notes") -> Dict[
        str, Any]:
        """
        Add a comment or work note to an existing ServiceNow incident.
        Args:
            incident_id: The sys_id of the incident to add comment to
            comment: The comment text to add
            comment_type: Type of comment - either "work_notes" (internal) or "comments" (customer visible)
        Returns:
            Dictionary containing the updated incident
        """
        logger.info(f"Adding comments {comment} to Incident {incident_id}")
        if comment_type not in ["work_notes", "comments"]:
            return {"error": True, "message": "comment_type must be either 'work_notes' or 'comments'"}

        endpoint = f"/table/incident/{incident_id}"
        update_data = {comment_type: comment}
        return self._make_servicenow_request(endpoint, method="PUT", data=update_data)

    def servicenow_incidents_add_comments_bulk(self, comments_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add comments or work notes to multiple ServiceNow incidents in bulk.
        This reduces the number of tool calls needed for MCP server operations.

        Args:
            comments_data: List of dictionaries, each containing comment data for an incident.
                          Required keys: 'incident_id', 'comment'
                          Optional keys: 'comment_type' (defaults to 'work_notes')

                          Example:
                          [
                              {
                                  'incident_id': 'sys_id_1',
                                  'comment': 'This is a work note',
                                  'comment_type': 'work_notes'
                              },
                              {
                                  'incident_id': 'sys_id_2',
                                  'comment': 'This is a customer comment',
                                  'comment_type': 'comments'
                              }
                          ]
        Returns:
            Dictionary containing:
            - 'success_count': Number of successfully updated incidents
            - 'error_count': Number of failed comment additions
            - 'results': List of results for each comment addition
            - 'successful_updates': List of successfully updated incidents
            - 'failed_updates': List of failed updates with error details
        """
        logger.info(f"Adding comments to {len(comments_data)} ServiceNow incidents in bulk")

        if not comments_data or not isinstance(comments_data, list):
            return {"error": True, "message": "comments_data must be a non-empty list"}

        results = []
        successful_updates = []
        failed_updates = []
        success_count = 0
        error_count = 0

        for i, comment_data in enumerate(comments_data):
            try:
                # Validate required fields
                if not isinstance(comment_data, dict):
                    error_result = {
                        "index": i,
                        "error": True,
                        "message": "Each comment entry must be a dictionary"
                    }
                    results.append(error_result)
                    failed_updates.append(error_result)
                    error_count += 1
                    continue

                if 'incident_id' not in comment_data or 'comment' not in comment_data:
                    error_result = {
                        "index": i,
                        "error": True,
                        "message": "Each comment entry must have 'incident_id' and 'comment' keys"
                    }
                    results.append(error_result)
                    failed_updates.append(error_result)
                    error_count += 1
                    continue

                # Extract comment data
                incident_id = comment_data['incident_id']
                comment = comment_data['comment']
                comment_type = comment_data.get('comment_type', 'work_notes')

                # Validate comment_type
                if comment_type not in ["work_notes", "comments"]:
                    error_result = {
                        "index": i,
                        "incident_id": incident_id,
                        "error": True,
                        "message": "comment_type must be either 'work_notes' or 'comments'"
                    }
                    results.append(error_result)
                    failed_updates.append(error_result)
                    error_count += 1
                    continue

                logger.info(f"Adding {comment_type} to incident {i + 1}/{len(comments_data)}: {incident_id}")

                # Add comment using existing function
                result = self.servicenow_incident_add_comment(incident_id, comment, comment_type)

                # Add index and original data for tracking
                result['index'] = i
                result['incident_id'] = incident_id
                result['comment_type'] = comment_type
                results.append(result)

                if result.get('error'):
                    failed_updates.append({
                        "index": i,
                        "incident_id": incident_id,
                        "comment_type": comment_type,
                        "comment": comment,
                        "error": result.get('message', 'Unknown error')
                    })
                    error_count += 1
                else:
                    successful_updates.append({
                        "index": i,
                        "incident_id": incident_id,
                        "comment_type": comment_type,
                        "comment_length": len(comment),
                        "comment_preview": comment[:50] + "..." if len(comment) > 50 else comment
                    })
                    success_count += 1

            except Exception as e:
                error_result = {
                    "index": i,
                    "error": True,
                    "message": f"Exception occurred: {str(e)}",
                    "comment_data": comment_data
                }
                results.append(error_result)
                failed_updates.append(error_result)
                error_count += 1
                logger.error(f"Exception adding comment to incident {i + 1}: {str(e)}")

        summary = {
            "success_count": success_count,
            "error_count": error_count,
            "total_count": len(comments_data),
            "results": results,
            "successful_updates": successful_updates,
            "failed_updates": failed_updates
        }

        logger.info(f"Bulk comment addition completed: {success_count} successful, {error_count} failed")
        return summary

    def servicenow_resolve_incident(self, incident_id: str, resolution_notes: str,
                                    close_code: str = "Solved (Permanently)") -> Dict[str, Any]:
        """
        Resolve a ServiceNow incident by setting it to resolved state.
        Args:
            incident_id: The sys_id of the incident to resolve
            resolution_notes: Notes describing how the incident was resolved
            close_code: The close code for the incident (default: "Solved (Permanently)")
        Returns:
            Dictionary containing the updated incident
        """
        logger.info(f"Resolving ServiceNow Incident {incident_id}")
        endpoint = f"/table/incident/{incident_id}"
        update_data = {
            "state": "6",  # 6 = Resolved state in ServiceNow
            "close_notes": resolution_notes,
            "close_code": close_code,
            "resolved_at": "javascript:gs.nowDateTime()",  # Current timestamp
            "work_notes": f"Incident resolved: {resolution_notes}"
        }
        return self._make_servicenow_request(endpoint, method="PUT", data=update_data)

    def _check_servicenow_health(self) -> Dict[str, Any]:
        """
        Check if the ServiceNow API is reachable.
        Returns:
            Dictionary containing health status
        """
        logger.info("Checking ServiceNow Api Health")
        try:
            result = self._make_servicenow_request("/table/sys_user", params={"sysparm_limit": "1"},
                                                   check_servicenow_health=False)
            if "result" in result or "records" in result or (isinstance(result, dict) and not result.get("error")):
                return {"status": "healthy"}
            return {"status": "unhealthy"}
        except Exception as e:
            logger.error("ServiceNow Health check failed " + str(e))
            return {"status": "unhealthy", "error": str(e)}


os.environ['SERVICENOW_BASE_URL'] = "http://localhost:5001/api/now"
os.environ["SERVICENOW_USER"] = "your_servicenow_username"
os.environ["SERVICENOW_PASSWORD"] = "your_servicenow_password"



servicenow_tools = ServiceNowTools()
# response = servicenow_tools.create_servicenow_incident("Test Incident", "This is a test incident")
# print(response)
response = servicenow_tools.get_servicenow_incidents(query="number=INC1000005^ORnumber=INC10000061^ORnumber=INC1000007")
print(len(response['result']))