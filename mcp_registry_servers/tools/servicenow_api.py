#!/usr/bin/env python3
"""
Fake ServiceNow API Server
Compatible with ServiceNow REST API for incidents and users
Stores data in SQLite database
"""

from flask import Flask, request, jsonify
import sqlite3
import json
import os
from datetime import datetime, timezone
import uuid
import base64
import logging
from typing import Dict, Any, List, Optional

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Database setup
DB_FILE = os.getenv('DB_FILE', 'servicenow_incidents.db')


def init_database():
    """Initialize the SQLite database with incidents and users tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create incidents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            sys_id TEXT PRIMARY KEY,
            number TEXT UNIQUE NOT NULL,
            short_description TEXT,
            description TEXT,
            state INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 5,
            urgency INTEGER DEFAULT 3,
            impact INTEGER DEFAULT 3,
            category TEXT,
            subcategory TEXT,
            assigned_to TEXT,
            assignment_group TEXT,
            caller_id TEXT,
            opened_by TEXT,
            opened_at TEXT,
            updated_at TEXT,
            resolved_at TEXT,
            closed_at TEXT,
            resolution_notes TEXT,
            work_notes TEXT,
            active boolean DEFAULT 1
        )
    ''')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sys_user (
            sys_id TEXT PRIMARY KEY,
            user_name TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            title TEXT,
            department TEXT,
            location TEXT,
            manager TEXT,
            active BOOLEAN DEFAULT 1,
            locked_out BOOLEAN DEFAULT 0,
            created_on TEXT,
            updated_on TEXT
        )
    ''')

    # Create indexes for faster searches
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_incident_number ON incidents(number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_incident_state ON incidents(state)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_incident_priority ON incidents(priority)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_username ON sys_user(user_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_email ON sys_user(email)')

    # Insert some default users if table is empty
    cursor.execute('SELECT COUNT(*) FROM sys_user')
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        default_users = [
            {
                'sys_id': str(uuid.uuid4()),
                'user_name': 'admin',
                'first_name': 'System',
                'last_name': 'Administrator',
                'email': 'admin@company.com',
                'phone': '+1-555-0100',
                'title': 'System Administrator',
                'department': 'IT',
                'location': 'Corporate HQ',
                'manager': '',
                'active': 1,
                'locked_out': 0,
                'created_on': get_current_timestamp(),
                'updated_on': get_current_timestamp()
            },
            {
                'sys_id': str(uuid.uuid4()),
                'user_name': 'john.smith',
                'first_name': 'John',
                'last_name': 'Smith',
                'email': 'john.smith@company.com',
                'phone': '+1-555-0101',
                'title': 'IT Support Specialist',
                'department': 'IT',
                'location': 'Corporate HQ',
                'manager': '',
                'active': 1,
                'locked_out': 0,
                'created_on': get_current_timestamp(),
                'updated_on': get_current_timestamp()
            },
            {
                'sys_id': str(uuid.uuid4()),
                'user_name': 'jane.doe',
                'first_name': 'Jane',
                'last_name': 'Doe',
                'email': 'jane.doe@company.com',
                'phone': '+1-555-0102',
                'title': 'Service Manager',
                'department': 'IT',
                'location': 'Corporate HQ',
                'manager': '',
                'active': 1,
                'locked_out': 0,
                'created_on': get_current_timestamp(),
                'updated_on': get_current_timestamp()
            }
        ]

        for user in default_users:
            cursor.execute('''
                INSERT INTO sys_user (
                    sys_id, user_name, first_name, last_name, email, phone,
                    title, department, location, manager, active, locked_out,
                    created_on, updated_on
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['sys_id'], user['user_name'], user['first_name'], user['last_name'],
                user['email'], user['phone'], user['title'], user['department'],
                user['location'], user['manager'], user['active'], user['locked_out'],
                user['created_on'], user['updated_on']
            ))

    conn.commit()
    conn.close()


def generate_incident_number():
    """Generate a ServiceNow-style incident number"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM incidents')
    count = cursor.fetchone()[0]
    conn.close()
    return f"INC{count + 1000001:07d}"


def get_current_timestamp():
    """Get current timestamp in ServiceNow format"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def dict_factory(cursor, row):
    """Convert sqlite row to dictionary"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def authenticate_request():
    """Simple authentication check"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False

    # Accept both Basic auth and Bearer token for flexibility
    if auth_header.startswith('Basic ') or auth_header.startswith('Bearer '):
        return True

    return False


def format_incident_response(incident: Dict[str, Any]) -> Dict[str, Any]:
    """Format incident data for API response"""
    # Map state numbers to display values
    state_map = {
        1: "New",
        2: "In Progress",
        3: "On Hold",
        6: "Resolved",
        7: "Closed",
        8: "Canceled"
    }

    priority_map = {
        1: "1 - Critical",
        2: "2 - High",
        3: "3 - Moderate",
        4: "4 - Low",
        5: "5 - Planning"
    }

    return {
        "sys_id": incident["sys_id"],
        "number": incident["number"],
        "short_description": incident["short_description"],
        "description": incident["description"],
        "state": {
            "value": str(incident["state"]),
            "display_value": state_map.get(incident["state"], "Unknown")
        },
        "priority": {
            "value": str(incident["priority"]),
            "display_value": priority_map.get(incident["priority"], "Unknown")
        },
        "urgency": str(incident["urgency"]),
        "impact": str(incident["impact"]),
        "category": incident["category"],
        "subcategory": incident["subcategory"],
        "assigned_to": incident["assigned_to"],
        "assignment_group": incident["assignment_group"],
        "caller_id": incident["caller_id"],
        "opened_by": incident["opened_by"],
        "opened_at": incident["opened_at"],
        "sys_updated_on": incident["updated_at"],
        "resolved_at": incident["resolved_at"],
        "closed_at": incident["closed_at"],
        "close_notes": incident["resolution_notes"],
        "work_notes": incident["work_notes"]
    }


def format_user_response(user: Dict[str, Any]) -> Dict[str, Any]:
    """Format user data for API response"""
    return {
        "sys_id": user["sys_id"],
        "user_name": user["user_name"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "name": f"{user['first_name']} {user['last_name']}".strip(),
        "email": user["email"],
        "phone": user["phone"],
        "title": user["title"],
        "department": user["department"],
        "location": user["location"],
        "manager": user["manager"],
        "active": bool(user["active"]),
        "locked_out": bool(user["locked_out"]),
        "sys_created_on": user["created_on"],
        "sys_updated_on": user["updated_on"]
    }


@app.before_request
def before_request():
    """Authenticate requests"""
    if request.endpoint and request.endpoint != 'health_check':
        if not authenticate_request():
            return jsonify({
                "error": {
                    "message": "User Not Authenticated",
                    "detail": "Required to provide Auth information"
                }
            }), 401


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "fake-servicenow-api"}), 200


# ============================================================================
# INCIDENT ENDPOINTS
# ============================================================================

@app.route('/api/now/table/incident', methods=['POST'])
def create_incident():
    """Create a new incident"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"message": "Invalid JSON data"}}), 400

        # Generate sys_id and incident number
        sys_id = str(uuid.uuid4())
        number = generate_incident_number()
        timestamp = get_current_timestamp()

        # Extract fields from request
        incident_data = {
            'sys_id': sys_id,
            'number': number,
            'short_description': data.get('short_description', ''),
            'description': data.get('description', ''),
            'state': int(data.get('state', 1)),
            'priority': int(data.get('priority', 5)),
            'urgency': int(data.get('urgency', 3)),
            'impact': int(data.get('impact', 3)),
            'category': data.get('category', ''),
            'subcategory': data.get('subcategory', ''),
            'assigned_to': data.get('assigned_to', ''),
            'assignment_group': data.get('assignment_group', ''),
            'caller_id': data.get('caller_id', ''),
            'opened_by': data.get('opened_by', ''),
            'opened_at': timestamp,
            'updated_at': timestamp,
            'resolved_at': None,
            'closed_at': None,
            'resolution_notes': '',
            'work_notes': data.get('work_notes', ''),
            'active': True
        }

        # Insert into database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO incidents (
                sys_id, number, short_description, description, state, priority,
                urgency, impact, category, subcategory, assigned_to, assignment_group,
                caller_id, opened_by, opened_at, updated_at, resolved_at, closed_at,
                resolution_notes, work_notes, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            incident_data['sys_id'], incident_data['number'], incident_data['short_description'],
            incident_data['description'], incident_data['state'], incident_data['priority'],
            incident_data['urgency'], incident_data['impact'], incident_data['category'],
            incident_data['subcategory'], incident_data['assigned_to'], incident_data['assignment_group'],
            incident_data['caller_id'], incident_data['opened_by'], incident_data['opened_at'],
            incident_data['updated_at'], incident_data['resolved_at'], incident_data['closed_at'],
            incident_data['resolution_notes'], incident_data['work_notes'],
            incident_data['active']
        ))

        conn.commit()
        conn.close()

        # Return formatted response
        response = format_incident_response(incident_data)
        return jsonify({"result": response}), 201

    except Exception as e:
        app.logger.error(f"Error creating incident: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


@app.route('/api/now/table/incident', methods=['GET'])
def get_incidents():
    """Search/retrieve incidents with query parameters"""
    try:
        # Get query parameters
        sysparm_query = request.args.get('sysparm_query', '')
        sysparm_limit = request.args.get('sysparm_limit', '10000')
        sysparm_offset = request.args.get('sysparm_offset', '0')
        sysparm_fields = request.args.get('sysparm_fields', '')

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Build base query
        base_query = "SELECT * FROM incidents"
        params = []

        # Parse sysparm_query for basic filtering
        where_conditions = []
        if sysparm_query:
            # Handle OR conditions by splitting on '^OR'
            or_groups = sysparm_query.split('^OR')

            if len(or_groups) > 1:
                # Multiple OR conditions exist
                or_conditions = []
                for or_group in or_groups:
                    # Each OR group can have AND conditions
                    and_conditions = []
                    conditions = or_group.strip().split('^')

                    for condition in conditions:
                        condition = condition.strip()
                        if not condition:
                            continue

                        if '=' in condition:
                            field, value = condition.split('=', 1)
                            field = field.strip()
                            value = value.strip()

                            if field in ['state', 'priority', 'urgency', 'impact']:
                                and_conditions.append(f"{field} = ?")
                                params.append(int(value))
                            elif field in ['active']:
                                and_conditions.append(f"{field} = ?")
                                params.append(1 if value.lower() in ['true', '1'] else 0)
                            else:
                                and_conditions.append(f"{field} = ?")
                                params.append(value)
                        elif 'CONTAINS' in condition:
                            field, value = condition.split('CONTAINS', 1)
                            field = field.strip()
                            value = value.strip()
                            and_conditions.append(f"{field} LIKE ?")
                            params.append(f"%{value}%")
                        elif 'STARTSWITH' in condition:
                            field, value = condition.split('STARTSWITH', 1)
                            field = field.strip()
                            value = value.strip()
                            and_conditions.append(f"{field} LIKE ?")
                            params.append(f"{value}%")

                    if and_conditions:
                        # Group AND conditions with parentheses
                        or_conditions.append(f"({' AND '.join(and_conditions)})")

                if or_conditions:
                    where_conditions.append(f"({' OR '.join(or_conditions)})")

            else:
                # No OR conditions, handle as before (AND conditions only)
                conditions = sysparm_query.split('^')
                for condition in conditions:
                    condition = condition.strip()
                    if not condition:
                        continue

                    if '=' in condition:
                        field, value = condition.split('=', 1)
                        field = field.strip()
                        value = value.strip()

                        if field in ['state', 'priority', 'urgency', 'impact']:
                            where_conditions.append(f"{field} = ?")
                            params.append(int(value))
                        elif field in ['active']:
                            where_conditions.append(f"{field} = ?")
                            params.append(1 if value.lower() in ['true', '1'] else 0)
                        else:
                            where_conditions.append(f"{field} = ?")
                            params.append(value)
                    elif 'CONTAINS' in condition:
                        field, value = condition.split('CONTAINS', 1)
                        field = field.strip()
                        value = value.strip()
                        where_conditions.append(f"{field} LIKE ?")
                        params.append(f"%{value}%")
                    elif 'STARTSWITH' in condition:
                        field, value = condition.split('STARTSWITH', 1)
                        field = field.strip()
                        value = value.strip()
                        where_conditions.append(f"{field} LIKE ?")
                        params.append(f"{value}%")

        # Add WHERE clause if conditions exist
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)

        # Add ordering
        base_query += " ORDER BY opened_at DESC"

        # Add LIMIT and OFFSET
        try:
            limit = int(sysparm_limit)
            offset = int(sysparm_offset)
            base_query += f" LIMIT {limit} OFFSET {offset}"
        except ValueError:
            pass

        cursor.execute(base_query, params)
        incidents = cursor.fetchall()
        conn.close()

        # Format response
        results = []
        for incident in incidents:
            formatted_incident = format_incident_response(incident)

            # Filter fields if sysparm_fields is specified
            if sysparm_fields:
                fields = [f.strip() for f in sysparm_fields.split(',')]
                filtered_incident = {}
                for field in fields:
                    if field in formatted_incident:
                        filtered_incident[field] = formatted_incident[field]
                results.append(filtered_incident)
            else:
                results.append(formatted_incident)

        return jsonify({"result": results}), 200

    except Exception as e:
        app.logger.error(f"Error retrieving incidents: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


@app.route('/api/now/table/incident/<sys_id>', methods=['GET'])
def get_incident_by_id(sys_id):
    """Get specific incident by sys_id"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM incidents WHERE sys_id = ?', (sys_id,))
        incident = cursor.fetchone()
        conn.close()

        if not incident:
            return jsonify({"error": {"message": "No Record found"}}), 404

        response = format_incident_response(incident)
        return jsonify({"result": response}), 200

    except Exception as e:
        app.logger.error(f"Error retrieving incident {sys_id}: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


@app.route('/api/now/table/incident/<sys_id>', methods=['PUT', 'PATCH'])
def update_incident(sys_id):
    """Update an existing incident"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"message": "Invalid JSON data"}}), 400

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Check if incident exists
        cursor.execute('SELECT * FROM incidents WHERE sys_id = ?', (sys_id,))
        incident = cursor.fetchone()

        if not incident:
            conn.close()
            return jsonify({"error": {"message": "No Record found"}}), 404

        # Build update query
        update_fields = []
        params = []

        # Map of allowed update fields
        allowed_fields = {
            'short_description', 'description', 'state', 'priority', 'urgency',
            'impact', 'category', 'subcategory', 'assigned_to', 'assignment_group',
            'caller_id', 'resolution_notes', 'work_notes'
        }

        for field, value in data.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = ?")
                if field in ['state', 'priority', 'urgency', 'impact']:
                    params.append(int(value))
                else:
                    params.append(value)

        # Always update the updated_at timestamp
        update_fields.append("updated_at = ?")
        params.append(get_current_timestamp())

        # Handle state changes
        if 'state' in data:
            state = int(data['state'])
            if state == 6:  # Resolved
                update_fields.append("resolved_at = ?")
                params.append(get_current_timestamp())
            elif state == 7:  # Closed
                update_fields.append("closed_at = ?")
                params.append(get_current_timestamp())

        params.append(sys_id)

        update_query = f"UPDATE incidents SET {', '.join(update_fields)} WHERE sys_id = ?"
        cursor.execute(update_query, params)
        conn.commit()

        # Fetch updated incident
        cursor.execute('SELECT * FROM incidents WHERE sys_id = ?', (sys_id,))
        updated_incident = cursor.fetchone()
        conn.close()

        response = format_incident_response(updated_incident)
        return jsonify({"result": response}), 200

    except Exception as e:
        app.logger.error(f"Error updating incident {sys_id}: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


@app.route('/api/now/table/incident/<sys_id>', methods=['DELETE'])
def delete_incident(sys_id):
    """Delete an incident"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Check if incident exists
        cursor.execute('SELECT COUNT(*) FROM incidents WHERE sys_id = ?', (sys_id,))
        count = cursor.fetchone()[0]

        if count == 0:
            conn.close()
            return jsonify({"error": {"message": "No Record found"}}), 404

        cursor.execute('DELETE FROM incidents WHERE sys_id = ?', (sys_id,))
        conn.commit()
        conn.close()

        return jsonify({"result": {"sys_id": sys_id}}), 204

    except Exception as e:
        app.logger.error(f"Error deleting incident {sys_id}: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


# ============================================================================
# SYS_USER ENDPOINTS
# ============================================================================

@app.route('/api/now/table/sys_user', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"message": "Invalid JSON data"}}), 400

        if not data.get('user_name'):
            return jsonify({"error": {"message": "user_name is required"}}), 400

        # Generate sys_id
        sys_id = str(uuid.uuid4())
        timestamp = get_current_timestamp()

        # Extract fields from request
        user_data = {
            'sys_id': sys_id,
            'user_name': data.get('user_name'),
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'title': data.get('title', ''),
            'department': data.get('department', ''),
            'location': data.get('location', ''),
            'manager': data.get('manager', ''),
            'active': bool(data.get('active', True)),
            'locked_out': bool(data.get('locked_out', False)),
            'created_on': timestamp,
            'updated_on': timestamp
        }

        # Insert into database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO sys_user (
                    sys_id, user_name, first_name, last_name, email, phone,
                    title, department, location, manager, active, locked_out,
                    created_on, updated_on
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data['sys_id'], user_data['user_name'], user_data['first_name'],
                user_data['last_name'], user_data['email'], user_data['phone'],
                user_data['title'], user_data['department'], user_data['location'],
                user_data['manager'], user_data['active'], user_data['locked_out'],
                user_data['created_on'], user_data['updated_on']
            ))

            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"error": {"message": "User name already exists"}}), 400

        conn.close()

        # Return formatted response
        response = format_user_response(user_data)
        return jsonify({"result": response}), 201

    except Exception as e:
        app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


@app.route('/api/now/table/sys_user', methods=['GET'])
def get_users():
    """Search/retrieve users with query parameters"""
    try:
        # Get query parameters
        sysparm_query = request.args.get('sysparm_query', '')
        sysparm_limit = request.args.get('sysparm_limit', '10000')
        sysparm_offset = request.args.get('sysparm_offset', '0')
        sysparm_fields = request.args.get('sysparm_fields', '')

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Build base query
        base_query = "SELECT * FROM sys_user"
        params = []

        # Parse sysparm_query for basic filtering
        where_conditions = []
        if sysparm_query:
            # Simple parsing for common ServiceNow queries
            conditions = sysparm_query.split('^')
            for condition in conditions:
                if '=' in condition:
                    field, value = condition.split('=', 1)
                    if field in ['active', 'locked_out']:
                        where_conditions.append(f"{field} = ?")
                        params.append(1 if value.lower() in ['true', '1'] else 0)
                    else:
                        where_conditions.append(f"{field} = ?")
                        params.append(value)
                elif 'CONTAINS' in condition:
                    field, value = condition.split('CONTAINS', 1)
                    where_conditions.append(f"{field} LIKE ?")
                    params.append(f"%{value}%")
                elif 'STARTSWITH' in condition:
                    field, value = condition.split('STARTSWITH', 1)
                    where_conditions.append(f"{field} LIKE ?")
                    params.append(f"{value}%")

        # Add WHERE clause if conditions exist
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)

        # Add ordering
        base_query += " ORDER BY user_name ASC"

        # Add LIMIT and OFFSET
        try:
            limit = int(sysparm_limit)
            offset = int(sysparm_offset)
            base_query += f" LIMIT {limit} OFFSET {offset}"
        except ValueError:
            pass

        cursor.execute(base_query, params)
        users = cursor.fetchall()
        conn.close()

        # Format response
        results = []
        for user in users:
            formatted_user = format_user_response(user)

            # Filter fields if sysparm_fields is specified
            if sysparm_fields:
                fields = [f.strip() for f in sysparm_fields.split(',')]
                filtered_user = {}
                for field in fields:
                    if field in formatted_user:
                        filtered_user[field] = formatted_user[field]
                results.append(filtered_user)
            else:
                results.append(formatted_user)

        return jsonify({"result": results}), 200

    except Exception as e:
        app.logger.error(f"Error retrieving users: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


@app.route('/api/now/table/sys_user/<sys_id>', methods=['GET'])
def get_user_by_id(sys_id):
    """Get specific user by sys_id"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM sys_user WHERE sys_id = ?', (sys_id,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({"error": {"message": "No Record found"}}), 404

        response = format_user_response(user)
        return jsonify({"result": response}), 200

    except Exception as e:
        app.logger.error(f"Error retrieving user {sys_id}: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


@app.route('/api/now/table/sys_user/<sys_id>', methods=['PUT', 'PATCH'])
def update_user(sys_id):
    """Update an existing user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"message": "Invalid JSON data"}}), 400

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute('SELECT * FROM sys_user WHERE sys_id = ?', (sys_id,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return jsonify({"error": {"message": "No Record found"}}), 404

        # Build update query
        update_fields = []
        params = []

        # Map of allowed update fields
        allowed_fields = {
            'user_name', 'first_name', 'last_name', 'email', 'phone',
            'title', 'department', 'location', 'manager', 'active', 'locked_out'
        }

        for field, value in data.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = ?")
                if field in ['active', 'locked_out']:
                    params.append(1 if value else 0)
                else:
                    params.append(value)

        # Always update the updated_on timestamp
        update_fields.append("updated_on = ?")
        params.append(get_current_timestamp())

        params.append(sys_id)

        update_query = f"UPDATE sys_user SET {', '.join(update_fields)} WHERE sys_id = ?"

        try:
            cursor.execute(update_query, params)
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"error": {"message": "User name already exists"}}), 400

        # Fetch updated user
        cursor.execute('SELECT * FROM sys_user WHERE sys_id = ?', (sys_id,))
        updated_user = cursor.fetchone()
        conn.close()

        response = format_user_response(updated_user)
        return jsonify({"result": response}), 200

    except Exception as e:
        app.logger.error(f"Error updating user {sys_id}: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


@app.route('/api/now/table/sys_user/<sys_id>', methods=['DELETE'])
def delete_user(sys_id):
    """Delete a user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute('SELECT COUNT(*) FROM sys_user WHERE sys_id = ?', (sys_id,))
        count = cursor.fetchone()[0]

        if count == 0:
            conn.close()
            return jsonify({"error": {"message": "No Record found"}}), 404

        cursor.execute('DELETE FROM sys_user WHERE sys_id = ?', (sys_id,))
        conn.commit()
        conn.close()

        return jsonify({"result": {"sys_id": sys_id}}), 204

    except Exception as e:
        app.logger.error(f"Error deleting user {sys_id}: {str(e)}")
        return jsonify({"error": {"message": str(e)}}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": {"message": "Not Found"}}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": {"message": "Internal Server Error"}}), 500


if __name__ == '__main__':
    init_database()
    print("Fake ServiceNow API Server starting...")
    print("Database initialized successfully")
    print("Server running on http://localhost:5000")
    print("\nSupported endpoints:")
    print("\nIncident Management:")
    print("  Create incident: POST /api/now/table/incident")
    print("  Get incidents: GET /api/now/table/incident")
    print("  Get incident by ID: GET /api/now/table/incident/{sys_id}")
    print("  Update incident: PUT/PATCH /api/now/table/incident/{sys_id}")
    print("  Delete incident: DELETE /api/now/table/incident/{sys_id}")
    print("\nUser Management:")
    print("  Create user: POST /api/now/table/sys_user")
    print("  Get users: GET /api/now/table/sys_user")
    print("  Get user by ID: GET /api/now/table/sys_user/{sys_id}")
    print("  Update user: PUT/PATCH /api/now/table/sys_user/{sys_id}")
    print("  Delete user: DELETE /api/now/table/sys_user/{sys_id}")
    print("\nQuery Examples:")
    print("  Get active users: GET /api/now/table/sys_user?sysparm_query=active=true")
    print("  Search users by name: GET /api/now/table/sys_user?sysparm_query=first_nameCONTAINSJohn")
    print("  Get specific fields: GET /api/now/table/sys_user?sysparm_fields=sys_id,user_name,email")
    print("\nAuthentication: Include 'Authorization: Basic <token>' or 'Authorization: Bearer <token>' header")

    app.run(debug=True, host='0.0.0.0', port=5001)