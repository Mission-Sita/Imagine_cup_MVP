from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import json
from jsonschema import validate,ValidationError
from typing import Annotated, Sequence, TypedDict, Any, Dict,Union
from langchain_core.messages import BaseMessage,SystemMessage,AIMessage,ToolMessage,HumanMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
# from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool
from pydantic import create_model
import nest_asyncio 
from dotenv import load_dotenv
import os

load_dotenv()

def remove_descriptions(data, max_length=None):
    """
    Recursively remove description fields from JSON schema.
    If max_length is set, remove only descriptions longer than max_length.
    """
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
        print(f"---------Valid Arguments---------")
        return "Valid"
    except ValidationError as e:
        print(f"---------Invalid Arguments-------")
        return f"Invalid as {e}"
    

from typing import List,Union
MAP = {
    "string":str,
    "number":float,
    "integer":int,
    "boolean":bool,
    "array":List[str],
    "object":dict
}


def json_to_model(name,schema):
    fields = {}
    required = schema.get("required",[])
    properties = schema.get("properties",{})


    for prop,rules in properties.items():
        if "anyOf" in rules:
            possible = []
            for option in rules["anyOf"]:
                if option["type"] == "string":
                    possible.append(MAP["string"])
                elif option["type"] == "array":
                    possible.append(MAP["array"])

            fields[prop] = (Union[tuple(possible)],... if prop in required else None)

        else:
            py_type = MAP[rules["type"]]
            fields[prop] = (py_type, ... if prop in required else None)

    return create_model(name, **fields)

async def mcp_execute(session, tool_name: str, **kwargs):
    """Generic executor for ANY MCP tool."""
    result = await session.call_tool(tool_name, kwargs)
    return result

def build_tool_from_schema(tool_name,tool_description,tool_schema,session):
    new_tool_name = tool_name.replace("-","_")
    new_tool_name = new_tool_name+"_Args"
    Arg_model = json_to_model(new_tool_name,tool_schema)

    async def wrapper(**kwargs):
        try:
            return await mcp_execute(
                session=session,
                tool_name=tool_name,
                **kwargs
            )
        except Exception as e:
            return f"TOOL ERROR: {type(e).__name__}: {str(e)}"


    nest_asyncio.apply()

    def sync_wrapper(**kwargs):
        import asyncio
        return asyncio.get_event_loop().run_until_complete(wrapper(**kwargs))

    tool = StructuredTool.from_function(
        name=tool_name,
        description=tool_description,
        func=sync_wrapper,
        args_schema=Arg_model
    )

    return tool


def load_config() -> Union[Dict, None]:
    config_path = "mcp.json"

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

async def configure_mcp(mcp_servers):


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

        schema_path = "Input_schema.json"
        os.makedirs("schemas", exist_ok=True)
        with open("Input_schema.json", "w") as f:
            json.dump(input_schemas, f, indent=3)
            print(f"Schema Dumped at {schema_path}")

        return stack,input_schemas,tools_list,name_to_tool

    except Exception as e:
        print(f"Stack cloased due to some problem as {e}")
        
        await stack.aclose()

def pretty_print_result(result):
    print("\n" + "="*60)
    print("FINAL AGENT OUTPUT")
    print("="*60)

    for msg in result["messages"]:
        if msg.__class__.__name__ == "HumanMessage":
            print("\n🧑 USER:")
            print(msg.content)

        elif msg.__class__.__name__ == "AIMessage":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print("\n🤖 ASSISTANT (Tool Call Request):")
                print(f"  → Tool: {msg.tool_calls[0]['name']}")
                print(f"  → Args: {msg.tool_calls[0]['args']}")
            else:
                print("\n🤖 ASSISTANT:")
                print(msg.content)

        elif msg.__class__.__name__ == "ToolMessage":
            print("\n🛠️ TOOL RESPONSE:")
            print(msg.content)

        else:
            print("\n❓ UNKNOWN MESSAGE TYPE:")
            print(msg)
    
    print("\n" + "="*60 + "\n")
