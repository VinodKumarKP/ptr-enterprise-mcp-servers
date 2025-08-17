# Jira Server MCP Server

A comprehensive Model Context Protocol (MCP) server that provides Jira issue management capabilities. This server
enables AI assistants to interact with Jira instances to manage issues, search for tickets, add comments, and perform
various Jira operations.

## Features

### Issue Management

- **Get specific issues** by issue key with optional field expansion
- **Search issues** using JQL (Jira Query Language) with pagination
- **Create new issues** with comprehensive field support
- **Update existing issues** with flexible field modifications
- **Transition issues** between different workflow states

### Issue Operations

- **Add comments** to issues with optional visibility controls
- **Get available transitions** for workflow management
- **Health monitoring** to check Jira API connectivity and authentication

### Integration Capabilities

- **Secure authentication** using Jira API tokens
- **Comprehensive error handling** with detailed error messages
- **Flexible API operations** supporting GET, POST, PUT, and DELETE methods
- **Atlassian Document Format** support for rich text content

## Installation

### Prerequisites

- Jira Cloud instance access with API permissions
- Valid Jira API token (generated from Atlassian Account Settings)
- Python 3.11+

### Environment Configuration

Set up your Jira credentials as environment variables:

**Linux/Mac:**

```bash
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_USERNAME="your-email@company.com"
export JIRA_API_TOKEN="your-api-token"
```

**Windows:**

```cmd
set JIRA_BASE_URL=https://your-domain.atlassian.net
set JIRA_USERNAME=your-email@company.com
set JIRA_API_TOKEN=your-api-token
```

**Or create a `.env` file:**

```
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your-api-token
```

### Option 1: Direct UV Run (Recommended)

Use uv to run the server directly without local installation:

```json
{
  "jira-server": {
    "command": "uv",
    "args": [
      "run",
      "--with",
      "git+https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry.git",
      "jira-mcp-server"
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
  "jira-server": {
    "command": "jira-mcp-server",
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
  "jira-server": {
    "command": "uv",
    "args": [
      "run",
      "--directory",
      "/path/to/ptr_mcp_servers_registry",
      "jira-mcp-server"
    ]
  }
}
```

### Option 4: Local Docker Compose Setup

You can run the MCP server registry locally using Docker Compose.

#### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry.git
   cd ptr_mcp_servers_registry
   ```

2. **Set up environment variables:**
   ```bash
   export JIRA_BASE_URL="https://your-domain.atlassian.net"
   export JIRA_USERNAME="your-email@company.com"
   export JIRA_API_TOKEN="your-api-token"
   ```

3. **Start the Jira service:**
   ```bash
   make start-jira_server
   ```

4. **Configure your client to use the local server:**
   ```json
   {
     "jira-server": {
       "command":"npx",
       "args":["mcp-remote@latest","http://localhost:8004/mcp", "--allow-http"]
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
    "jira-server": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "git+https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry.git",
        "jira-mcp-server"
      ],
      "env": {
        "JIRA_BASE_URL": "https://your-domain.atlassian.net",
        "JIRA_USERNAME": "your-email@company.com",
        "JIRA_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

**Using remote server:**

```json
{
  "mcpServers": {
    "jira-server": {
      "command": "npx",
      "args": ["mcp-remote@latest", "http://your-server:8004/mcp", "--allow-http"]
    }
  }
}
```

### Jira API Token Setup

1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Give it a label and copy the generated token
4. Use your email as username and the token as password for API authentication

## Available Tools

### Core Issue Management

| Tool                | Purpose                    | Key Parameters                         |
|---------------------|----------------------------|----------------------------------------|
| `jira_get_issue`    | Get specific issue details | `issue_key`, `expand`                  |
| `jira_search`       | Search issues using JQL    | `jql`, `max_results`, `fields`         |
| `jira_create_issue` | Create new issues          | `project_key`, `issue_type`, `summary` |
| `jira_update_issue` | Update existing issues     | `issue_key`, `update_data`             |

### Issue Operations

| Tool                    | Purpose                | Key Parameters                          |
|-------------------------|------------------------|-----------------------------------------|
| `jira_transition_issue` | Change issue status    | `issue_key`, `transition_id`, `comment` |
| `jira_add_comment`      | Add comments to issues | `issue_key`, `comment`, `visibility`    |

### Utility Operations

| Tool                   | Purpose                   | Parameters  |
|------------------------|---------------------------|-------------|
| `get_jira_transitions` | Get available transitions | `issue_key` |
| `check_jira_health`    | Check API connectivity    | None        |

### Tool Details

#### `jira_search`

- **JQL Examples:**
    - `"project = PROJ AND status = 'To Do'"` - Project issues in To Do status
    - `"assignee = currentUser() AND status != Done"` - My open issues
    - `"created >= -7d"` - Issues created in last 7 days
    - `"priority = High AND resolution = Unresolved"` - High priority open issues

#### `jira_create_issue`

- **Issue Types:** Bug, Task, Story, Epic, Sub-task
- **Priority Levels:** Highest, High, Medium, Low, Lowest
- **Optional Fields:** description, priority, assignee, labels, custom_fields

#### `jira_transition_issue`

- **Common Transitions:** To Do → In Progress → Done
- **Custom Workflows:** Requires transition IDs from `get_jira_transitions`

#### `jira_add_comment`

- **Visibility Options:**
    - Public comments (default)
    - Role-based: `{"type": "role", "value": "Administrators"}`
    - Group-based: `{"type": "group", "value": "jira-users"}`

## Usage Examples

### Complete Issue Lifecycle

```python
# 1. Search for existing issues
issues = await jira_search("project = PROJ AND status = 'To Do'", max_results=10)

# 2. Create a new issue
new_issue = await jira_create_issue(
    project_key="PROJ",
    issue_type="Bug",
    summary="Login page not loading",
    description="Users report 500 error when accessing login page",
    priority="High",
    labels=["frontend", "urgent"]
)
issue_key = new_issue['key']

# 3. Add a comment
await jira_add_comment(
    issue_key,
    "Investigating the issue - checking server logs"
)

# 4. Get available transitions
transitions = await get_jira_transitions(issue_key)

# 5. Transition to In Progress
await jira_transition_issue(
    issue_key,
    transition_id="21",  # ID from transitions response
    comment="Starting work on this issue"
)

# 6. Update issue details
await jira_update_issue(issue_key, {
    "assignee": {"accountId": "user-account-id"},
    "priority": {"name": "Critical"}
})

# 7. Transition to Done
await jira_transition_issue(
    issue_key,
    transition_id="31",
    comment="Issue resolved - deployed fix to production"
)
```

### Search and Query Operations

```python
# Get all my assigned issues
my_issues = await jira_search("assignee = currentUser() AND resolution = Unresolved")

# Get recent bugs
recent_bugs = await jira_search(
    "project = PROJ AND issuetype = Bug AND created >= -14d",
    max_results=25
)

# Get high priority issues
urgent_issues = await jira_search(
    "priority in (Highest, High) AND status != Done",
    fields=["summary", "status", "assignee", "created"]
)

# Check system health
health_status = await check_jira_health()
```

## Jira Reference

### Common Issue Types

- **Bug** - Software defects
- **Task** - General work items
- **Story** - User stories (Agile)
- **Epic** - Large features
- **Sub-task** - Breakdown of larger items

### Priority Levels

- **Highest** - Critical issues requiring immediate attention
- **High** - Important issues to be resolved soon
- **Medium** - Standard priority (default)
- **Low** - Nice-to-have improvements
- **Lowest** - Future considerations

### JQL Operators

- `=` Equal to
- `!=` Not equal to
- `>`, `<`, `>=`, `<=` Comparison operators
- `IN`, `NOT IN` List membership
- `~` Contains text
- `AND`, `OR` Logical operators

### Common JQL Fields

- `project` - Project key
- `issuetype` - Issue type
- `status` - Current status
- `priority` - Priority level
- `assignee` - Assigned user
- `reporter` - Issue creator
- `created`, `updated` - Timestamps
- `resolution` - Resolution status

## Error Handling & Requirements

### Common Error Scenarios

- **Authentication**: Invalid API token or username
- **Authorization**: Insufficient permissions for projects/issues
- **Network**: Connectivity issues to Jira instance
- **Data**: Invalid issue keys, malformed JQL, or missing required fields
- **Rate Limiting**: Jira API throttling

### System Requirements

- **Python**: 3.11+ with `requests` library
- **Jira Access**: Cloud instance URL, valid API token, project permissions
- **Network**: HTTPS connectivity to Atlassian services
- **Permissions**: Project access, issue creation/editing rights

### Security Best Practices

- Store API tokens in environment variables (never in code)
- Use HTTPS for all Jira communications
- Implement proper Jira project permissions and roles
- Regularly rotate API tokens and monitor usage
- Enable Jira audit logging for API operations

## License & Contributing

This MCP server is part of
the [Capgemini Innersource MCP Servers Registry](https://github.com/Capgemini-Innersource/ptr_mcp_servers_registry).

For issues, feature requests, or contributions, please visit the main repository.
