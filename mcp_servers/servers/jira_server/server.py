import os
import sys

file_root = os.path.dirname(os.path.abspath(__file__))
path_list = [
    file_root,
    os.path.dirname(file_root),
    os.path.dirname(os.path.dirname(file_root)),
    os.path.dirname(os.path.dirname(os.path.dirname(file_root)))
]
for path in path_list:
    if path not in sys.path:
        sys.path.append(path)

import nest_asyncio  # Added import

nest_asyncio.apply()  # Added call

from mcp_servers.utils.jira_utils import JiraUtils
from mcp_server_core.servers.base_mcp_server.server import BaseMCPServer


class JiraServer(BaseMCPServer):
    """Jira MCP server implementation."""

    def __init__(self):
        """
        Initialize the Jira server.
        """
        super().__init__(self.base_directory(__file__),
                         object_list=[JiraUtils()],
                         source_file=__file__)


def main():
    """Main function to run the Jira server."""
    server = JiraServer()
    server.main()


if __name__ == "__main__":
    main()
