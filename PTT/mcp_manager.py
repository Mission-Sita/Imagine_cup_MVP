
from pydantic import create_model
from typing import List,Union
from langchain_core.tools import StructuredTool
import nest_asyncio 



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