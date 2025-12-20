from langchain_core.messages import SystemMessage,HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from mcp_configure import configure_mcp
from utils import validate_arguments,resolve_tool_name
from ptt_reasoning import PTTReasoningModule
from ptt_tree_manager import TaskTreeManager,TaskNode,NodeStatus
import json
import os
import asyncio



load_dotenv()

async def main():
    stack, GLOBAL_SCHEMA, tools, GLOBAL_NAME_TO_TOOL = await configure_mcp()

    llm = ChatOpenAI( 
        model="gpt-4o", 
        openai_api_key=os.getenv("OPEN_AI_API_KEY"), 
        openai_api_base=os.getenv("OPEN_AI_API_BASE")
        ).bind_tools(tools)



    # goal = "Assess the security posture of example.com"
    # target = "https://example.com"
    # constraints = {"scope": "public endpoints only"}
    goal = "gather informatoin about the target 192.168.128.2"
    target = "192.168.128.2"
    constraints = {"Aggressiveness":"Don't Start too Aggressive initially"}

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
            tool_used = task.get("tool_suggestion",None),
            tool_arguments = task.get("tool_arguments",{})
        )
        tree_manager.add_node(node)


    
    while True:

        candidates = tree_manager.get_candidate_tasks()[:10]
        if not candidates:
            print("All tasks completed or blocked.")
            break


        next_action_prompt = reasoning_module.get_next_action_prompt(available_tools)

        next_response = llm.invoke([SystemMessage(content="Select next task"), HumanMessage(content=next_action_prompt)])


        
        next_action = reasoning_module.parse_next_action_response(next_response.content)

        print(json.dumps(next_action,indent=2))
        selected_index = next_action.get("selected_task_index", 1) - 1
        selected_task = candidates[selected_index]
        tool_name = selected_task.tool_used
        tool_args = selected_task.tool_arguments


        tree_manager.update_node(
            selected_task.id,
            {"status": NodeStatus.IN_PROGRESS.value}
        )


        print(f"\nExecuting Task: {selected_task.description}| \n{tool_name}\n {tool_args} ===")

        tool_name_normalized = resolve_tool_name(tool_name,GLOBAL_SCHEMA.keys())

        if tool_name == 'manual':
            print(f"Description:\n{selected_task.description}\n")
            print(f"Ecpected Outcome:\n{next_action.get("expected_outcome","No Expected Outcome")}")
            
            await asyncio.to_thread(input, "User: ")


        elif tool_name_normalized in GLOBAL_NAME_TO_TOOL:
            
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
            tool_output = "Not Executed due to unknown reason"
   



        update_prompt = reasoning_module.get_tree_update_prompt(tool_output, selected_task)

        update_response = llm.invoke([SystemMessage(content="Update tree based on output"), HumanMessage(content=update_prompt)])


        node_updates, new_tasks = reasoning_module.parse_tree_update_response(update_response.content)


        tree_manager.update_node(selected_task.id, node_updates)

        print(node_updates)
        print(new_tasks)

        for t in new_tasks:

            tool_name = resolve_tool_name(t.get("tool_suggestion"),list(GLOBAL_SCHEMA.keys()))

            if tool_name in GLOBAL_SCHEMA.keys():

                node = TaskNode(
                    description=t["description"],
                    parent_id=tree_manager.root_id,
                    priority=t.get("priority", 5),
                    risk_level=t.get("risk_level", "low"),
                    tool_used=t.get("tool_suggestion"),
                    tool_arguments=t.get("tool_arguments", {})
                )
                tree_manager.add_node(node)


        print(reasoning_module.generate_strategic_summary())

        goal_check_prompt = reasoning_module.get_goal_check_prompt()

        goal_response = llm.invoke([SystemMessage(content="Check goal achievement"), HumanMessage(content=goal_check_prompt)])

        goal_status = reasoning_module.parse_goal_check_response(goal_response.content)

        if goal_status.get("goal_achieved", False):
            print("\n🎯 Goal Achieved!")
            print(goal_status)
            break


    await stack.aclose()

if __name__ == "__main__":
    asyncio.run(main())