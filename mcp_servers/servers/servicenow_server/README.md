# ServiceNow Server MCP Server

A comprehensive Model Context Protocol (MCP) server that provides ServiceNow incident management capabilities. This
server enables AI assistants to interact with ServiceNow instances to manage incidents, add comments, and perform
various ServiceNow operations.

## Features

### Incident Management

- **Fetch incidents** with customizable query filters
- **Create new incidents** with description and details
- **Update existing incidents** with flexible field modifications
- **Resolve incidents** with resolution notes and close codes

### Incident Operations

- **Add comments and work notes** to incidents (internal or customer-visible)
- **Get specific incidents** by sys_id for detailed information
- **Health monitoring** to check ServiceNow API connectivity

### Integration Capabilities

- **Secure authentication** using environment variables
- **Comprehensive error handling** with detailed error messages
- **Flexible API operations** supporting GET, POST, PUT, and PATCH methods

## Installation

### Prerequisites

- ServiceNow instance access with API permissions
- Valid ServiceNow credentials (username/password)
- Python 3.11+

### Environment Configuration

Set up your ServiceNow credentials as environment variables:

**Linux/Mac:**

```bash
export SERVICENOW_USER="your_username"
export SERVICENOW_PASSWORD="your_password"
```

**Windows:**

```cmd
set SERVICENOW_USER=your_username
set SERVICENOW_PASSWORD=your_password
```

**Or create a `.env` file:**

```
SERVICENOW_USER=your_username
SERVICENOW_PASSWORD=your_password
```

### Option 1: Direct UV Run (Recommended)

Use uv to run the server directly without local installation:

```json
{
  "servicenow-server": {
    "command": "uv",
    "args": [
      "run",
      "--with",
      "git+https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry.git",
      "servicenow-mcp-server"
    ]
  }
}
```

### Option 2: Pip Install + Run

Install the package first, then run the server:

```bash
pip install git+https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry.git
```

Then configure your MCP client:

```json
{
  "servicenow-server": {
    "command": "servicenow-mcp-server",
    "args": []
  }
}
```

### Option 3: Local Clone + UV Run

Clone the repository locally and run with uv:

```bash
git clone https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry.git
```

Then configure your MCP client:

```json
{
  "servicenow-server": {
    "command": "uv",
    "args": [
      "run",
      "--directory",
      "/path/to/ptr_mcp_servers_registry",
      "servicenow-mcp-server"
    ]
  }
}
```

### Option 4: Local Docker Compose Setup

You can run the MCP server registry locally using Docker Compose. This is ideal for development and testing purposes.

#### Prerequisites

- Docker and Docker Compose installed
- Make utility installed
- `jq` command-line JSON processor

#### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry.git
   cd ptr_mcp_servers_registry
   ```

2. **Set up environment variables:**
   ```bash
   export SERVICENOW_USER="your_username"
   export SERVICENOW_PASSWORD="your_password"
   ```

3. **Build and start all services:**
   ```bash
   make start-all
   ```

4. **Or start the ServiceNow service specifically:**
   ```bash
   make start-servicenow_server
   ```

5. **List available services:**
   ```bash
   make list-services
   ```

6. **Configure your client to use the local server:**
   In your client configuration (e.g., Claude Desktop), add the server with the local URL:
   ```json
   {
     "servicenow-server": {
       "command":"npx",
    	"args":["mcp-remote@latest","http://localhost:8003/mcp", "--allow-http"]
     }
   }
   ```

#### Available Make Commands

- `make start-all` - Start all services using Docker Compose
- `make stop-all` - Stop all services
- `make start-servicenow_server` - Start the ServiceNow service
- `make stop-servicenow_server` - Stop the ServiceNow service
- `make restart-servicenow_server` - Restart the ServiceNow service
- `make list-services` - List all available services
- `make docker-build` - Build the Docker image
- `make generate-compose` - Generate Docker Compose file

### Option 5: Remote Server Deployment

For production use or when you want to share the MCP server with multiple users, you can deploy it to a remote server.

#### Prerequisites

- Remote server with Docker and Docker Compose installed
- SSH access to the remote server
- Domain name or public IP address
- ServiceNow instance credentials

#### Deployment Steps

1. **Deploy to your remote server:**
   ```bash
   # SSH into your remote server
   ssh user@your-remote-server.com
   
   # Clone the repository
   git clone https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry.git
   cd ptr_mcp_servers_registry
   
   # Set up environment variables
   export SERVICENOW_USER="your_username"
   export SERVICENOW_PASSWORD="your_password"
   
   # Build and start services
   make start-all
   ```

2. **Configure firewall (if needed):**
   ```bash
   # Allow traffic on port 8003 (ServiceNow server port)
   # Check the servers_config/servicenow_server.json for the list of ports to be opened
   sudo ufw allow 8003
   ```

3. **Configure your client to use the remote server:**
   In your client configuration, use the remote server URL:
   ```json
   {
     "servicenow-server": {
       "command":"npx",
    	"args":["mcp-remote@latest","http://remote-ip:8003/mcp", "--allow-http"]
     }
   }
   ```

## Configuration

### Claude Desktop

Add to your `claude_desktop_config.json`:

**Using uv command (Recommended):**

```json
{
  "mcpServers": {
    "servicenow-server": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "git+https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry.git",
        "servicenow-mcp-server"
      ],
      "env": {
        "SERVICENOW_USER": "your_username",
        "SERVICENOW_PASSWORD": "your_password"
      }
    }
  }
}
```

**Using remote server:**

```json
{
  "mcpServers": {
    "servicenow-server": {
      "command": "npx",
      "args": ["mcp-remote@latest", "http://your-server:8003/mcp", "--allow-http"]
    }
  }
}
```

### ServiceNow Instance Configuration

- **Base URL**: Update `SERVICENOW_BASE_URL` in the utils code to match your ServiceNow instance
- **Authentication**: Uses basic authentication with username/password
- **API Permissions**: Ensure your ServiceNow user has appropriate permissions:
    - `incident` table read/write access
    - API access enabled
    - `sys_user` table read access (for assignments)

## Available Tools

### Core Incident Management

| Tool                            | Purpose                       | Key Parameters                     |
|---------------------------------|-------------------------------|------------------------------------|
| `get_servicenow_incidents`      | Fetch incidents with filters  | `query` (optional)                 |
| `create_servicenow_incident`    | Create new incidents          | `short_description`, `description` |
| `update_servicenow_incident`    | Update existing incidents     | `incident_id`, `update_data`       |
| `get_servicenow_incident_by_id` | Get specific incident details | `incident_id`                      |

### Incident Operations

| Tool                              | Purpose                 | Key Parameters                                  |
|-----------------------------------|-------------------------|-------------------------------------------------|
| `servicenow_incident_add_comment` | Add comments/work notes | `incident_id`, `comment`, `comment_type`        |
| `servicenow_resolve_incident`     | Resolve incidents       | `incident_id`, `resolution_notes`, `close_code` |

### System Operations

| Tool                      | Purpose                | Parameters |
|---------------------------|------------------------|------------|
| `check_servicenow_health` | Check API connectivity | None       |

### Tool Details

#### `get_servicenow_incidents`

- **Query Examples:**
    - `"active=true"` - Active incidents
    - `"priority=1"` - Critical priority
    - `"assigned_to=user_sys_id"` - Assigned to user
    - `"state=2^priority=1"` - In progress AND critical

#### `servicenow_incident_add_comment`

- **Comment Types:**
    - `"work_notes"` - Internal notes (default)
    - `"comments"` - Customer-visible comments

#### `servicenow_resolve_incident`

- **Common Close Codes:**
    - `"Solved (Permanently)"` (default)
    - `"Solved (Workaround)"`
    - `"Not Solved (Not Reproducible)"`
    - `"Closed/Resolved by Caller"`

#### `update_servicenow_incident`

- **Common Fields:**
    - `state`: 1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed
    - `priority`: 1=Critical, 2=High, 3=Moderate, 4=Low, 5=Planning
    - `assigned_to`: User sys_id
    - `work_notes`: Internal notes

## Usage Examples

### Complete Incident Lifecycle

```python
# 1. Create incident
incident = await create_servicenow_incident(
    "Email server down", 
    "Users unable to access email since 9 AM"
)
incident_id = incident['result']['sys_id']

# 2. Add work note
await servicenow_incident_add_comment(
    incident_id,
    "Investigating root cause - checking server logs",
    "work_notes"
)

# 3. Update status and assign
await update_servicenow_incident(incident_id, {
    "state": "2",  # In Progress
    "priority": "2",  # High
    "assigned_to": "user_sys_id"
})

# 4. Add customer comment
await servicenow_incident_add_comment(
    incident_id,
    "We are working on resolving your email access issue",
    "comments"
)

# 5. Resolve incident
await servicenow_resolve_incident(
    incident_id,
    "Issue resolved by restarting email service and updating configuration",
    "Solved (Permanently)"
)
```

### Query and Search Operations

```python
# Get critical incidents
critical = await get_servicenow_incidents("priority=1^state!=6^state!=7")

# Get my assigned incidents  
my_incidents = await get_servicenow_incidents("assigned_to=my_user_sys_id^active=true")

# Get recent incidents
recent = await get_servicenow_incidents("sys_created_on>javascript:gs.daysAgoStart(7)")

# Check system health
status = await check_servicenow_health()
```

## Error Handling & Requirements

### Common Error Scenarios

- **Authentication**: Invalid credentials or expired sessions
- **Authorization**: Insufficient permissions for incident operations
- **Network**: Connectivity issues to ServiceNow instance
- **Data**: Invalid field values, missing required fields, or malformed requests
- **Rate Limiting**: ServiceNow API throttling

### System Requirements

- **Python**: 3.11+ with `requests` library
- **ServiceNow Access**: Instance URL, valid credentials, API permissions
- **Network**: HTTPS connectivity to ServiceNow instance
- **Permissions**: `incident` table read/write, `sys_user` table read access

### Security Best Practices

- Store credentials in environment variables (never in code)
- Use HTTPS for all ServiceNow communications
- Implement proper ServiceNow role-based access controls
- Regularly rotate passwords and monitor API usage
- Enable ServiceNow audit logging for API operations

## License & Contributing

This MCP server is part of
the [Capgemini Innersource MCP Servers Registry](https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry).

For issues, feature requests, or contributions, please visit the main repository.

