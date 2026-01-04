from jsonschema import validate,ValidationError
from typing import List
import json
import ast

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
    if isinstance(inputs_args, str):
        try:
            inputs_args = json.loads(inputs_args)
        except:
            try:
                inputs_args = ast.literal_eval(inputs_args)
            except Exception:
                
                return f"Critical Error: Could not parse arguments string into JSON. Data: {inputs_args}"
    try:
        validate(instance=inputs_args, schema=schema)
        return "Valid"
    except ValidationError as e:
        return f"Invalid as {e}"
    

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