from typing import Union,Dict
import json
from contextlib import AsyncExitStack
from mcp import ClientSession,StdioServerParameters,stdio_client
from utils import remove_descriptions
from mcp_manager import build_tool_from_schema



def load_config() -> Union[Dict, None]:
    config_path = "/Users/pashantraj/Desktop/Repos/imagine_cup/Imagine_cup_MVP/mcp.json"

    try:
        with open(config_path) as f:
            config = json.load(f)

            mcp_servers = config.get("mcpServers", {})

            if not mcp_servers:
                print("No MCP servers found")

            return mcp_servers

    except Exception as e:
        print(f"Unable to open Config at path {config_path} as {e}")
        return None

async def configure_mcp():
    mcp_servers = load_config()
    input_schemas = {}
    name_to_tool = {}
    tools_list = []
    stack = AsyncExitStack()
    await stack.__aenter__()

    try:
        for server_name, server_info in mcp_servers.items():
            print(f"Connecting to server {server_name}...")

            server_param = StdioServerParameters(
                command=server_info["command"],
                args=server_info["args"],
                env=server_info.get("env")
            )

            read, write = await stack.enter_async_context(stdio_client(server_param))

            session = await stack.enter_async_context(
                ClientSession(read_stream=read, write_stream=write)
            )

            await session.initialize()
            print(f"Session initialized for {server_name}")



            server_tools = await session.list_tools()
            for tool in server_tools.tools:
                clean_schema = remove_descriptions(tool.inputSchema, max_length=200)  # or None
                input_schemas[tool.name] = clean_schema
                create_tool = build_tool_from_schema(tool.name,tool.description,clean_schema,session)
                name_to_tool[tool.name] = create_tool
                tools_list.append(create_tool)


        return stack,input_schemas,tools_list,name_to_tool

    except Exception as e:
        print(f"Stack cloased due to some problem as {e}")
        
        await stack.aclose()