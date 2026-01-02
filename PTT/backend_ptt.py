import os
import json
import asyncio
from dotenv import load_dotenv, find_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from mcp_configure import configure_mcp
from ptt_utils import validate_arguments, resolve_tool_name
from ptt_reasoning import PTTReasoningModule
from ptt_tree_manager import TaskTreeManager, TaskNode, NodeStatus
from md_logger import setup_md_logger
from agent_io import AgentIO

load_dotenv(find_dotenv())


class PTTAgent:
    def __init__(self, goal: str, target: str, constraints: dict, io: AgentIO):
        self.goal = goal
        self.target = target
        self.constraints = constraints
        self.io = io

        self.stack = None
        self.GLOBAL_SCHEMA = None
        self.tools = None
        self.GLOBAL_NAME_TO_TOOL = None

        self.llm = None
        self.tree_manager = TaskTreeManager()
        self.reasoning_module = None
        self.logger = setup_md_logger("logging.md")

   

    async def setup(self):
        self.stack, self.GLOBAL_SCHEMA, self.tools, self.GLOBAL_NAME_TO_TOOL = (
            await configure_mcp()
        )

        self.llm = ChatOpenAI(
            model="gpt-4.1",
            openai_api_key=os.getenv("OPEN_AI_API_KEY"),
            openai_api_base=os.getenv("OPEN_AI_API_BASE"),
        ).bind_tools(self.tools)

        self.tree_manager.initialize_tree(
            self.goal, self.target, self.constraints
        )
        self.reasoning_module = PTTReasoningModule(self.tree_manager)

    

    async def initialize_tree(self):
        available_tools = list(self.GLOBAL_NAME_TO_TOOL.keys())

        prompt = self.reasoning_module.get_tree_initialization_prompt(
            self.goal,
            self.target,
            self.constraints,
            available_tools,
        )

        response = self.llm.invoke(
            [
                SystemMessage(content="You are a cybersecurity agent."),
                HumanMessage(content=prompt),
            ]
        )

        parsed = self.reasoning_module.parse_tree_initialization_response(
            response.content
        )

        self.logger.info(f"Initial Tasks\n{parsed}")
        
        for task in parsed["initial_tasks"]:
            node = TaskNode(
                description=task["description"],
                parent_id=self.tree_manager.root_id,
                priority=task.get("priority", 5),
                risk_level=task.get("risk_level", "low"),
                tool_used=task.get("tool_suggestion"),
                tool_arguments=task.get("tool_arguments", {}),
            )
            self.tree_manager.add_node(node)

        await self.io.output(
            "status",
            "Initial task tree created",
        )
        await self.io.info(
            "initial_tasks",
            f"Initial Tasks\n{parsed}"
            )

    

    async def run_reasoning_loop(self):
        available_tools = list(self.GLOBAL_NAME_TO_TOOL.keys())

        while True:
            candidates = self.tree_manager.get_candidate_tasks()[:10]
            if not candidates:
                break

            prompt = self.reasoning_module.get_next_action_prompt(
                available_tools
            )

            response = self.llm.invoke(
                [
                    SystemMessage(content="Select next task"),
                    HumanMessage(content=prompt),
                ]
            )

            decision = self.reasoning_module.parse_next_action_response(
                response.content
            )

            self.logger.info(
                f"{decision['rationale']}\n"
                f"Expected Outcome: {decision['expected_outcome']}"
            )
            await self.io.info(
                "Running_loop",
                f"{decision['rationale']}\nExpected Outcome: {decision['expected_outcome']}"
            )
            task = candidates[decision["selected_task_index"] - 1]

            await self.execute_task(task, decision)

            if await self.check_goal():
                break

    

    async def execute_task(self, task: TaskNode, decision: dict):
        self.tree_manager.update_node(
            task.id, {"status": NodeStatus.IN_PROGRESS.value}
        )

        await self.io.output(
            "log",
            f"Executing task: {task.description}",
        )

        tool_name = task.tool_used
        tool_args = task.tool_arguments
        normalized_tool = resolve_tool_name(
            tool_name, self.GLOBAL_SCHEMA.keys()
        )

        self.logger.info(f"Executing Task: {task.description}")
        self.logger.info(f"Tool: {tool_name}")
        self.logger.info(f"Args: {tool_args}")

        
        if tool_name == "manual":
            await self.io.output(
                "question",
                decision.get(
                    "expected_outcome",
                    "Manual input required",
                ),
            )

            user_input = await self.io.input()
            tool_output = f"User input: {user_input}"


        elif normalized_tool in self.GLOBAL_NAME_TO_TOOL:
            validation = validate_arguments(
                tool_args,
                self.GLOBAL_SCHEMA[normalized_tool],
            )

            if validation != "Valid":
                tool_output = f"Invalid arguments: {validation}"
            else:
                try:
                    result = self.GLOBAL_NAME_TO_TOOL[
                        normalized_tool
                    ].run(tool_args)
                    tool_output = result.content[0].text
                except Exception as e:
                    tool_output = f"Tool error: {e}"
        else:
            tool_output = "Tool not executed"

        self.logger.info(f"Raw Tool Output:\n{tool_output}")

        summarized = await self.summarize_tool_output(
            tool_output, task
        )

        await self.io.output(
            "summary",
            summarized,
        )

        await self.update_tree(task, summarized)

    

    async def update_tree(self, task: TaskNode, output: str):
        prompt = self.reasoning_module.get_tree_update_prompt(
            output, task
        )

        response = self.llm.invoke(
            [
                SystemMessage(content="Update tree"),
                HumanMessage(content=prompt),
            ]
        )

        updates, new_tasks = (
            self.reasoning_module.parse_tree_update_response(
                response.content
            )
        )

        self.tree_manager.update_node(task.id, updates)

        for t in new_tasks:
            node = TaskNode(
                description=t["description"],
                parent_id=self.tree_manager.root_id,
                priority=t.get("priority", 5),
                risk_level=t.get("risk_level", "low"),
                tool_used=t.get("tool_suggestion"),
                tool_arguments=t.get("tool_arguments", {}),
            )
            self.tree_manager.add_node(node)

    

    async def check_goal(self) -> bool:
        prompt = self.reasoning_module.get_goal_check_prompt()

        response = self.llm.invoke(
            [
                SystemMessage(content="Check goal"),
                HumanMessage(content=prompt),
            ]
        )

        status = self.reasoning_module.parse_goal_check_response(
            response.content
        )

        if status.get("goal_achieved"):
            await self.io.output(
                "status",
                "🎯 Goal Achieved",
            )
            return True

        return False

    

    async def summarize_tool_output(
        self, output: str, task: TaskNode
    ) -> str:
        if len(output) < 4000:
            return output

        prompt = f"""
Summarize pentesting tool output.

Task: {task.description}
Tool: {task.tool_used}

Keep:
- IPs, ports, vulns, creds
- Errors
- Exploitable info

Tool Output:
{output}
"""

        response = self.llm.invoke(
            [
                SystemMessage(content="Summarize tool output"),
                HumanMessage(content=prompt),
            ]
        )

        return response.content.strip()

    

    async def close(self):
        if self.stack:
            await self.stack.aclose()



async def run_agent(agent: PTTAgent):
    try:
        await agent.setup()
        await agent.initialize_tree()
        await agent.run_reasoning_loop()
        await agent.io.output(
            "status",
            "Agent finished",
        )
    except Exception as e:
        await agent.io.output(
            "error",
            str(e),
        )
    finally:
        await agent.close()
