from enum import Enum
from utils import load_config

def load_tool_enum():
    mcp_servers, _ = load_config()

    return Enum(
        "ToolName",
        {
            server_name.replace("-", "_").upper(): server_name
            for server_name in mcp_servers.keys()
        },
        type=str
    )


