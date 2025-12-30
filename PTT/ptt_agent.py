import os
import json
import asyncio
from dotenv import load_dotenv , find_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from mcp_configure import configure_mcp
from ptt_utils import validate_arguments, resolve_tool_name
from ptt_reasoning import PTTReasoningModule
from ptt_tree_manager import TaskTreeManager, TaskNode, NodeStatus
from md_logger import setup_md_logger
load_dotenv(find_dotenv())

class PTTAgent:
    def __init__(self, goal: str, target: str, constraints: dict):
        self.goal = goal
        self.target = target
        self.constraints = constraints

        self.stack = None
        self.GLOBAL_SCHEMA = None
        self.tools = None
        self.GLOBAL_NAME_TO_TOOL = None

        self.llm = None
        self.tree_manager = TaskTreeManager()
        self.reasoning_module = None

        self.logger = setup_md_logger("logging.md") ## Adding logger

    async def setup(self):
        """Initialize MCP stack and LLM"""
        self.stack, self.GLOBAL_SCHEMA, self.tools, self.GLOBAL_NAME_TO_TOOL = await configure_mcp()

        self.llm = ChatOpenAI(
            model="gpt-4.1",
            openai_api_key=os.getenv("OPEN_AI_API_KEY"),
            openai_api_base=os.getenv("OPEN_AI_API_BASE"),
        ).bind_tools(self.tools)

        self.tree_manager.initialize_tree(self.goal, self.target, self.constraints)
        self.reasoning_module = PTTReasoningModule(self.tree_manager)

    async def initialize_tree(self):
        """Ask LLM to generate initial task tree"""
        available_tools = list(self.GLOBAL_NAME_TO_TOOL.keys())

        init_prompt = self.reasoning_module.get_tree_initialization_prompt(
            self.goal, self.target, self.constraints, available_tools
        )

        response = self.llm.invoke([
            SystemMessage(content="You are a cybersecurity agent."),
            HumanMessage(content=init_prompt)
        ])

        parsed = self.reasoning_module.parse_tree_initialization_response(response.content)

        for task in parsed["initial_tasks"]:
            node = TaskNode(
                description=task["description"],
                parent_id=self.tree_manager.root_id,
                priority=task.get("priority", 5),
                risk_level=task.get("risk_level", "low"),
                tool_used=task.get("tool_suggestion"),
                tool_arguments=task.get("tool_arguments", {})
            )
            self.tree_manager.add_node(node)

    async def run_reasoning_loop(self):
        """Main reasoning + execution loop"""
        available_tools = list(self.GLOBAL_NAME_TO_TOOL.keys())

        while True:
            candidates = self.tree_manager.get_candidate_tasks()[:10]
            if not candidates:
                print("All tasks completed or blocked.")
                break

            prompt = self.reasoning_module.get_next_action_prompt(available_tools)
            response = self.llm.invoke([
                SystemMessage(content="Select next task"),
                HumanMessage(content=prompt)
            ])

            next_action = self.reasoning_module.parse_next_action_response(response.content)
            #print(f"{next_action['rationale']}\nExpexted Outcome: {next_action['expected_outcome']}\n")
            self.logger.info(
                f"{next_action['rationale']}\n"
                f"Expected Outcome: {next_action['expected_outcome']}"
            )


            selected_task = candidates[next_action["selected_task_index"] - 1]
            await self.execute_task(selected_task, next_action)

            if await self.check_goal():
                break

    async def execute_task(self, task: TaskNode, decision: dict):
        """Execute a selected task and update tree"""
        self.tree_manager.update_node(task.id, {"status": NodeStatus.IN_PROGRESS.value})

        tool_name = task.tool_used
        tool_args = task.tool_arguments
        normalized_tool = resolve_tool_name(tool_name, self.GLOBAL_SCHEMA.keys())

        # print(f"\nExecuting Task: {task.description}")
        # print(f"Tool: {tool_name}")
        # print(f"Args: {tool_args}")
        self.logger.info(f"Executing Task: {task.description}")
        self.logger.info(f"Tool: {tool_name}")
        self.logger.info(f"Args: {tool_args}")

        if tool_name == "manual":
            print(decision.get("expected_outcome", "No expected outcome"))
            await asyncio.to_thread(input, "User action required: ")
            tool_output = "Manual step completed."

        elif normalized_tool in self.GLOBAL_NAME_TO_TOOL:
            validation = validate_arguments(tool_args, self.GLOBAL_SCHEMA[normalized_tool])
            if validation != "Valid":
                tool_output = f"Invalid arguments: {validation}"
            else:
                try:
                    result = self.GLOBAL_NAME_TO_TOOL[normalized_tool].run(tool_args)
                    tool_output = result.content[0].text
                except Exception as e:
                    tool_output = f"Tool error: {e}"
        else:
            tool_output = "Tool not executed."

        self.logger.info(f"Tool Output:\n{tool_output}")


        await self.update_tree(task, tool_output)

    async def update_tree(self, task: TaskNode, tool_output: str):
        """Update task tree based on tool output"""
        prompt = self.reasoning_module.get_tree_update_prompt(tool_output, task)
        response = self.llm.invoke([
            SystemMessage(content="Update tree based on output"),
            HumanMessage(content=prompt)
        ])

        node_updates, new_tasks = self.reasoning_module.parse_tree_update_response(response.content)
        self.tree_manager.update_node(task.id, node_updates)

        for t in new_tasks:
            node = TaskNode(
                description=t["description"],
                parent_id=self.tree_manager.root_id,
                priority=t.get("priority", 5),
                risk_level=t.get("risk_level", "low"),
                tool_used=t.get("tool_suggestion"),
                tool_arguments=t.get("tool_arguments", {})
            )
            self.tree_manager.add_node(node)

        print(self.reasoning_module.generate_strategic_summary())
        self.tree_manager.to_graphviz("task_tree_latest")
        self.logger.info("Updated task tree visualization → task_tree_latest.png")


    async def check_goal(self) -> bool:
        """Check if goal is achieved"""
        prompt = self.reasoning_module.get_goal_check_prompt()
        response = self.llm.invoke([
            SystemMessage(content="Check goal achievement"),
            HumanMessage(content=prompt)
        ])

        status = self.reasoning_module.parse_goal_check_response(response.content)
        if status.get("goal_achieved"):
            # print(json.dumps(status,indent=3))
            # print("\n🎯 Goal Achieved!")
            # print(status)
            # return True
           
            self.logger.info("🎯 Goal Achieved")
            self.logger.info(json.dumps(status, indent=3))
            return True
        
        return False
    

    

    async def close(self):
        if self.stack:
            await self.stack.aclose()
