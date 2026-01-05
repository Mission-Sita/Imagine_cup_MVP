import os
import json
import asyncio
import ast
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
        await self.io.output("status", "Initializing Tools & LLM...")
        self.stack, self.GLOBAL_SCHEMA, self.tools, self.GLOBAL_NAME_TO_TOOL = (
            await configure_mcp()
        )

        self.llm = ChatOpenAI(
            model="gpt-4o",
            openai_api_key=os.getenv("OPEN_AI_API_KEY"),
            openai_api_base=os.getenv("OPEN_AI_API_BASE"),
        ).bind_tools(self.tools)

        self.tree_manager.initialize_tree(
            self.goal, self.target, self.constraints
        )
        self.reasoning_module = PTTReasoningModule(self.tree_manager)
        
        await self.io.output("status", "Setup Complete. Tools Ready.")
    

    async def initialize_tree(self):
        await self.io.output("status", "Generating Initial Attack Plan...")
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
        await self.io.output("log",f"Structure: {parsed.get("analysis","No structure is defined")}")

        structure = parsed.get("structure",None)
        if structure is not None:
            for item in structure:
                await self.io.output("status",f"status: {item["type"]}\nName: {item["name"]}\nDescription: {item['description']}\nJustification: {item['justification']}")
                # await self.io.output("status",f"Description: {item['description']}\nJustification: {item['justification']}")


        self.logger.info(f"Structre and Initial Tasks\n{json.dumps(parsed,indent=2)}") # This log is for local MD file

        await self.io.output("log",f"Number of Tasks Added: {len(parsed["initial_tasks"])}")
        
        for task in parsed["initial_tasks"]:
            
            #Adding the Logs for WebApp
            await self.io.output("log",f"Task Description: {task["description"]}")
            await self.io.output("log",f"tool: {task.get("tool_suggestion")}, Args: {task.get("tool_arguments", {})}")
            await self.io.output("log","-------------------------------------------------------------------------------------------------------------------")

            node = TaskNode(
                description=task["description"],
                parent_id=self.tree_manager.root_id,
                priority=task.get("priority", 5),
                risk_level=task.get("risk_level", "low"),
                tool_used=task.get("tool_suggestion"),
                tool_arguments=task.get("tool_arguments", {}),
            )
            self.tree_manager.add_node(node)
            
        await self.io.output("status", "Task Tree Created.")
        
    
    async def run_reasoning_loop(self):
        available_tools = list(self.GLOBAL_NAME_TO_TOOL.keys())

        while True:
            candidates = self.tree_manager.get_candidate_tasks()[:10]
            if not candidates:
                await self.io.output("status", "No more candidate tasks found.")
                break
            await self.io.output("status", "Thinking about next move...")

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

            if not decision:
                self.logger.error("Failed to parse decision")
                continue
            log_msg = f"{decision.get('rationale', 'No rationale')}\nExpected: {decision.get('expected_outcome', '')}"
            self.logger.info(log_msg)
            
            await self.io.output("info", log_msg)

            task = candidates[decision["selected_task_index"] - 1]

            is_completed = await self.execute_task(task, decision)

            if is_completed:
                break

    

    async def execute_task(self, task: TaskNode, decision: dict)->bool:
        self.tree_manager.update_node(
            task.id, {"status": NodeStatus.IN_PROGRESS.value}
        )

        await self.io.output("log", f"⚡ Executing: {task.description}")
        

        tool_name = task.tool_used
        tool_args = task.tool_arguments
        if isinstance(tool_args, str):
            try:
                tool_args = ast.literal_eval(tool_args)
            except:
                pass

        normalized_tool = resolve_tool_name(
            tool_name, self.GLOBAL_SCHEMA.keys()
        )

        self.logger.info(f"Executing Task: {task.description}")
        self.logger.info(f"Tool: {tool_name}")
        self.logger.info(f"Args: {tool_args}")

        await self.io.output("tool_use", {
            "name": tool_name,
            "args": tool_args
        })


        if tool_name == "manual":
            question = decision.get("expected_outcome", "Manual input required")
            await self.io.output("question", question)
            await self.io.output("status", "Waiting for User Input...")

            user_input = await self.io.input()
            tool_output = f"User input: {user_input}"
            await self.io.output("log", f"👤 User Replied: {user_input}")

        elif normalized_tool in self.GLOBAL_NAME_TO_TOOL:
            validation = validate_arguments(
                tool_args,
                self.GLOBAL_SCHEMA[normalized_tool],
            )

            if validation != "Valid":
                tool_output = f"Invalid arguments: {validation}"
                await self.io.output("error", tool_output)
            else:
                try:
                    await self.io.output("status", f"Running {normalized_tool}...")
                    result = await self.GLOBAL_NAME_TO_TOOL[
                        normalized_tool
                    ].ainvoke(tool_args)
                    if hasattr(result, 'content'):
                        tool_output = str(result.content)
                    else:
                        tool_output = str(result)
                    
                except Exception as e:
                    tool_output = f"Tool error: {e}"
                    await self.io.output("error", str(e))
        else:
            tool_output = f"Tool '{tool_name}' not found or not executed"
            await self.io.output("error", tool_output)

        self.logger.info(f"Raw Tool Output:\n{tool_output}")
        await self.io.output("log", f"📄 Output received ({len(tool_output)} chars)")
        await self.io.output("status", "Analyzing results...")

        summarized = await self.summarize_tool_output(
            tool_output, task
        )

        
        await self.io.output("summary", summarized)
        is_completed = await self.update_tree(task, summarized)
        return is_completed
    

    async def update_tree(self, task: TaskNode, output: str)->bool:
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
        if await self.check_goal():
            return True
        await self.io.output("log", f"Updates:\nstatus: {updates["status"]}\nfindings: {updates["findings"]}\noutput_summary: {updates["output_summary"]}\n")
        
        if new_tasks is not None:
            await self.io.output("status", f"Number of New Tasks Added {len(new_tasks)}")
         
            for t in new_tasks:
                await self.io.output("log",f"Task Description: {t["description"]}")
                await self.io.output("log",f"tool: {t.get("tool_suggestion")}, Args: {t.get("tool_arguments", {})}")
                await self.io.output("log","---------------------------------------------------------------------------------------------------------------")

                node = TaskNode(
                    description=t["description"],
                    parent_id=task.id,
                    priority=t.get("priority", 5),
                    risk_level=t.get("risk_level", "low"),
                    tool_used=t.get("tool_suggestion"),
                    tool_arguments=t.get("tool_arguments", {}),
                )
                self.tree_manager.add_node(node)
            

        return False
    

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
            await self.io.output("status", "🎯 Goal Achieved!")
            await self.io.output("success", f"Final Result {json.dumps(status,indent=2)}\n")
            return True

        return False

    

    async def summarize_tool_output(
        self, output: str, task: TaskNode
    ) -> str:
        
        prompt = f"""
 You are a penetration testing assistant.

    Summarize the following tool output for task tree reasoning.

    Task:
    - Description: {task.description}
    - Tool Used: {task.tool_used}
    - Tool Agrguments {task.tool_arguments}

    Requirements:
    - Preserve actionable findings (IPs, ports, vulnerabilities, credentials, flags)
    - Preserve errors or anomalies
    - Remove noise, banners, repetition
    - Output MUST be concise (max 300 words)
    - Use bullet points where possible

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




