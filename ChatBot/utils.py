import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import json
from langchain_core.tools import StructuredTool
from pydantic import create_model
from jsonschema import validate, ValidationError
from typing import Union
from typing import List

def resolve_tool_name(llm_tool_name: str, available_tools: List[str]) -> str:
    """
    Resolve an LLM-provided tool name to a known available tool.
    """
    if not llm_tool_name:
        raise ValueError("LLM provided empty tool name")

    llm_tool_name = llm_tool_name.strip()


    if llm_tool_name in available_tools:
        return llm_tool_name

    candidate = llm_tool_name.split(".")[-1]
    if candidate in available_tools:
        return candidate


    for tool in available_tools:
        if llm_tool_name.endswith(tool):
            return tool


    return "not_found"

def remove_descriptions(data, max_length=None):
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            if key == "description":
                if max_length is None:
                    continue
                elif isinstance(value, str) and len(value) > max_length:
                    continue
            new_dict[key] = remove_descriptions(value, max_length)
        return new_dict
    elif isinstance(data, list):
        return [remove_descriptions(item, max_length) for item in data]
    return data

def validate_arguments(inputs_args, schema):
    try:
        validate(instance=inputs_args, schema=schema)
        #print("---------Valid Arguments---------")
        return "Valid"
    except ValidationError as e:
        #print("---------Invalid Arguments---------")
        return f"Invalid as {e}"

MAP = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict
}

def json_to_model(name, schema):
    fields = {}
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    for prop, rules in properties.items():
        if "anyOf" in rules:
            possible = []
            for option in rules["anyOf"]:
                if option["type"] in MAP:
                    possible.append(MAP[option["type"]])
            fields[prop] = (Union[tuple(possible)], ... if prop in required else None)
        else:
            py_type = MAP.get(rules["type"], str)
            fields[prop] = (py_type, ... if prop in required else None)
    return create_model(name, **fields)

async def mcp_execute(session, tool_name: str, **kwargs):
    result = await session.call_tool(tool_name, kwargs)
    return result

def build_tool_from_schema(tool_name, tool_description, tool_schema, session):
    new_tool_name = tool_name.replace("-", "_") + "_Args"
    Arg_model = json_to_model(new_tool_name, tool_schema)
    
    # Define an async function directly
    async def wrapper(**kwargs):
        try:
            result = await session.call_tool(tool_name, kwargs)
            # MCP results usually come back as objects with a 'content' attribute
            # We convert to string for the LLM
            return "\n".join([c.text for c in result.content if hasattr(c, 'text')])
        except Exception as e:
            return f"TOOL ERROR: {str(e)}"

    # Create the tool using coroutine (coroutine for async support)
    tool = StructuredTool.from_function(
        name=tool_name,
        description=tool_description,
        coroutine=wrapper, # Use coroutine instead of func for async
        args_schema=Arg_model
    )
    return tool

def load_config():
    # Get the path to the current file (Chatbot/utils.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go UP one level, then into Shared_Services
    config_path = os.path.join(current_dir, "..", "Shared_Services", "mcp.json")
    
    # Resolve the .. to a clean absolute path
    config_path = os.path.abspath(config_path)

    try:
        with open(config_path) as f:
            config = json.load(f)
            return config.get("mcpServers", {}), os.path.dirname(config_path) # Return the folder path too!
    except Exception as e:
        print(f"Unable to open Config: {e}")
        return None, None

async def configure_mcp():
    mcp_servers, base_path = load_config()
    server_session_dict = {}
    tool_to_server = {}
    input_schemas = {}
    name_to_tool = {}
    tools = []
    stack = AsyncExitStack()
    await stack.__aenter__()
    try:
        for server_name, server_info in mcp_servers.items():

            cmd = server_info["command"]
            if cmd == "python" or cmd == "python3":
                cmd = sys.executable 
            resolved_args = []
            for arg in server_info["args"]:
                potential_path = os.path.join(base_path, arg)
                if os.path.exists(potential_path):
                    resolved_args.append(potential_path)
                else:
                    resolved_args.append(arg)
            server_param = StdioServerParameters(
                command=cmd,
                args=resolved_args,   
                env=server_info.get("env")
            )
            read, write = await stack.enter_async_context(stdio_client(server_param))
            session = await stack.enter_async_context(
                ClientSession(read_stream=read, write_stream=write)
            )
            await session.initialize()
            print(f"Session initialized for {server_name}")
            server_session_dict[server_name] = session
            server_tools = await session.list_tools()
            for tool in server_tools.tools:
                clean_schema = remove_descriptions(tool.inputSchema, max_length=200)
                input_schemas[tool.name] = clean_schema
                tool_to_server[tool.name] = server_name
                create_tool = build_tool_from_schema(
                    tool.name, tool.description, clean_schema, session
                )
                tools.append(create_tool)
                name_to_tool[tool.name] = create_tool
        return tools,input_schemas,name_to_tool,stack
    except Exception as e:
        print(f"Stack closed due to problem: {e}")
        await stack.aclose()
        raise