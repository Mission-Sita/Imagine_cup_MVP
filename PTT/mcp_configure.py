import sys
import os
from typing import Union, Dict
import json
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, stdio_client
from utils import remove_descriptions
from mcp_manager import build_tool_from_schema

def load_config() -> Union[Dict, None]:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(BASE_DIR, "mcp.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
            return config.get("mcpServers", {})
    except Exception as e:
        print(f"Unable to open Config at path {config_path} as {e}")
        return None

async def configure_mcp():
    mcp_servers = load_config()
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    input_schemas = {}
    name_to_tool = {}
    tools_list = []
    stack = AsyncExitStack()
    await stack.__aenter__()

    try:
        for server_name, server_info in mcp_servers.items():
            print(f"Connecting to server {server_name}...")

            
            cmd = server_info["command"]
            if cmd == "python" or cmd == "python3":
                cmd = sys.executable 
            resolved_args = []
            for arg in server_info["args"]:
                
                potential_path = os.path.join(BASE_DIR, arg)
                if os.path.exists(potential_path):
                    resolved_args.append(potential_path)
                else:
                    resolved_args.append(arg)
            
            
            current_env = os.environ.copy()
            if "env" in server_info and server_info["env"]:
                current_env.update(server_info["env"])

            server_param = StdioServerParameters(
                command=cmd,
                args=resolved_args, 
                env=current_env
            )

            read, write = await stack.enter_async_context(stdio_client(server_param))

            session = await stack.enter_async_context(
                ClientSession(read_stream=read, write_stream=write)
            )

            await session.initialize()
            print(f" Session initialized for {server_name}")

            server_tools = await session.list_tools()
            for tool in server_tools.tools:
                clean_schema = remove_descriptions(tool.inputSchema, max_length=200)
                input_schemas[tool.name] = clean_schema
                create_tool = build_tool_from_schema(tool.name, tool.description, clean_schema, session)
                name_to_tool[tool.name] = create_tool
                tools_list.append(create_tool)

        return stack, input_schemas, tools_list, name_to_tool

    except Exception as e:
        print(f"Stack closed due to error: {e}")
        await stack.aclose()
        raise e