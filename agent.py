
from contextlib import AsyncExitStack
from langchain_core.messages import SystemMessage,HumanMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
from mcp_configure import configure_mcp
from utils import validate_arguments
import json
from ptt_reasoning import PTTReasoningModule
from ptt_tree_manager import TaskTreeManager,TaskNode
import asyncio
import sys
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


load_dotenv()

async def main():
    stack, GLOBAL_SCHEMA, tools, GLOBAL_NAME_TO_TOOL = await configure_mcp()

    llm = ChatOpenAI( 
        model="openai/gpt-4o", 
        openai_api_key=os.getenv("OPEN_AI_API_KEY"), 
        openai_api_base=os.getenv("OPEN_AI_API_BASE")
        ).bind_tools(tools)



    goal = "Assess the security posture of example.com"
    target = "https://example.com"
    constraints = {"scope": "public endpoints only"}

    tree_manager = TaskTreeManager()
    tree_manager.initialize_tree(goal, target, constraints)
    reasoning_module = PTTReasoningModule(tree_manager)

    available_tools = list(GLOBAL_NAME_TO_TOOL.keys())


    init_prompt = reasoning_module.get_tree_initialization_prompt(goal, target, constraints, available_tools)

    init_msg = HumanMessage(content=init_prompt)

    init_response = llm.invoke([SystemMessage(content="You are a cybersecurity agent."), init_msg])


    parsed_init = reasoning_module.parse_tree_initialization_response(init_response.content)


    for task in parsed_init["initial_tasks"]:
        node = TaskNode(
            description=task["description"],
            parent_id=tree_manager.root_id,
            priority=task.get("priority", 5),
            risk_level=task.get("risk_level", "low"),
            tool_arguments = task["tool_arguments"]
        )
        tree_manager.add_node(node)


    
    while True:

        candidates = tree_manager.get_candidate_tasks()
        if not candidates:
            print("All tasks completed or blocked.")
            break


        next_action_prompt = reasoning_module.get_next_action_prompt(available_tools)

        next_response = llm.invoke([SystemMessage(content="Select next task"), HumanMessage(content=next_action_prompt)])


        if next_response.tool_calls:
            print(f"Next Response toolcall: \n{json.dumps(next_response.tool_calls[0]["args"],indent=2)}")
            next_action = reasoning_module.parse_next_action_response(json.dumps(next_response.tool_calls[0]["args"],indent=2))
        else:
            next_action = reasoning_module.parse_next_action_response(next_response.content)


        selected_index = next_action.get("selected_task_index", 1) - 1
        selected_task = candidates[selected_index]
        tool_name = next_action.get("tool")

        if not tool_name:
            tool_output = "Task blocked: No executable tool provided"
            tree_manager.update_node(selected_task.id, {
                "status": "blocked",
                "findings": "No MCP tool available for this task"
            })
            continue

        command = next_action.get("command", "")
        tool_args = next_action.get("tool_arguments",{})

        print(f"\nExecuting Task: {selected_task.description}| \n{tool_name}\n {tool_args} ===")

        tool_name_normalized = resolve_tool_name(tool_name,GLOBAL_SCHEMA.keys())

        if tool_name_normalized in GLOBAL_NAME_TO_TOOL:
            
            validation = validate_arguments(tool_args, GLOBAL_SCHEMA[tool_name_normalized])

            if validation != "Valid":

                print(f"Argument validation failed: {validation}")

                tool_output = f"Tool execution skipped due to invalid arguments: {validation}"

            else:

                try:
                    result = GLOBAL_NAME_TO_TOOL[tool_name_normalized].run(tool_args)

                    tool_output = result.content[0].text

                except Exception as e:

                    print(f"Tool execution error: {e}")

                    tool_output = f"Tool execution failed with error: {e}"
        else:
            if not tool_name_normalized or tool_name_normalized == "not_found":
                tree_manager.update_node(selected_task.id, {
                    "status": "blocked",
                    "findings": "Task is not executable by any connected MCP tool"
                })
                continue    



        update_prompt = reasoning_module.get_tree_update_prompt(tool_output, command, selected_task,tool_name,tool_args)

        update_response = llm.invoke([SystemMessage(content="Update tree based on output"), HumanMessage(content=update_prompt)])


        node_updates, new_tasks = reasoning_module.parse_tree_update_response(update_response.content)


        tree_manager.update_node(selected_task.id, node_updates)


        for t in new_tasks:

            tool_name = resolve_tool_name(t.get("tool_suggestion"),GLOBAL_SCHEMA.keys())

            if tool_name in GLOBAL_SCHEMA.keys():

                node = TaskNode(
                    description=t["description"],
                    parent_id=tree_manager.root_id,
                    priority=t.get("priority", 5),
                    risk_level=t.get("risk_level", "low")
                )
                tree_manager.add_node(node)


        print(reasoning_module.generate_strategic_summary())

        goal_check_prompt = reasoning_module.get_goal_check_prompt()

        goal_response = llm.invoke([SystemMessage(content="Check goal achievement"), HumanMessage(content=goal_check_prompt)])

        goal_status = reasoning_module.parse_goal_check_response(goal_response.content)

        if goal_status.get("goal_achieved", False):
            print("\n🎯 Goal Achieved!")
            break


    await stack.aclose()

if __name__ == "__main__":
    asyncio.run(main())