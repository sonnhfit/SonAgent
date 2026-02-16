import json
import logging
import os
from datetime import datetime
from pathlib import Path

import yaml
from croniter import croniter

from sonagent.brain import AgentBrain
from sonagent.persistence import Belief, Environment, ScheduleJob, Task
from sonagent.tools import GitManager, LocalCodeManager
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, memory_path, skills, config: dict, conversation_id: str = None) -> None:
        self.config = config

        logger.debug(f"Init memory with path {memory_path}.")

        # Initialize brain with dynamic skill loading and search
        # Pass conversation_id if provided, otherwise brain will generate default
        self.brain = AgentBrain(
            config=config, 
            skills_manager=skills,
            conversation_id=conversation_id
        )
        
        # Store conversation_id for reference
        self.conversation_id = self.brain.conversation_id
        logger.debug(f"Agent initialized with conversation_id: {self.conversation_id}")
        
        # Keep skills for backward compatibility
        self.skills = skills
        self.skills_dict = {}

        logger.info("--------- Start skill.---------")
        # Start skills through brain
        self.brain.load_and_index_skills()
        logger.info("--------- Start Done.---------")

        # git manager
        github = self.config.get("github")
        if github and github.get("enabled"):
            self.git_manager = GitManager(
                username=github.get("username"),
                repo_name=github.get("repo_name"),
                token=github.get("token"),
                local_repo_path=github.get("local_repo_path"),
            )
        else:
            self.git_manager = LocalCodeManager(
                local_repo_path=self.config.get("user_data_dir")
            )

        # load skill dict
        self.init_skills_dict()

    def remove_skill(self, skill_name):
        # With dynamic skill loading, we can't remove skills from a YAML file.
        # Instead, users should delete the skill file from the skills directory.
        # We'll reload skills to reflect the current state of the directory.
        
        skill_file_path = Path(self.git_manager.local_repo_path).joinpath('skills', f"{skill_name}.py")
        
        if skill_file_path.exists():
            return f"Skill '{skill_name}' exists as a file. To remove it, delete the file: {skill_file_path}"
        else:
            # The skill might have been already deleted or never existed
            self.reload_skills()
            return f"Skill '{skill_name}' not found in skills directory. Skills have been reloaded to reflect current state."

    def init_skills_dict(self) -> None:
        for skill in self.skills.get_all_skills():
            self.skills_dict[str(skill.__class__.__name__)] = skill

    def get_beliefs_for_planner(self, ids: list) -> list:
        list_belief = Belief.get_belief_by_ids(ids=ids)
        return list_belief

    def show_skills(self) -> str:
        self.skills.reload_skills()
        return ", ".join(self.skills_dict.keys())

    def _reload_skills(self):
        logger.info("--------- reload skill.---------")
        # Use brain to reload and reindex skills
        self.brain.reload_skills()
        # Also update skills dict for backward compatibility
        self.skills_dict = {}
        self.init_skills_dict()

        logger.info("--------- reload Done.---------")

    def reload_skills(self) -> str:
        self._reload_skills()
        return self.show_skills()

    def sync_beliefs(self) -> None:
        logger.debug("Start syncing beliefs to memory.")
        # TODO: Implement memory sync with new memory system
        logger.info("Finish syncing beliefs to memory.")

    def create_beslief(self, text: str, description: str) -> None:
        try:
            belief = Belief(text=text, description=description)
            Belief.session.add(belief)
            Belief.session.commit()
            logger.debug("Finish Create new belief.")
            # Belief.commit()
        except Exception as e:
            logger.error(f"Error create belief: {e}")

    def clear_all_beliefs(self) -> None:
        Belief.session.query(Belief).delete()
        Belief.session.commit()

        logger.debug("Finish delete all belief.")

    def delete_everything(self) -> bool:
        try:
            self.clear_all_beliefs()
            # TODO: Implement memory clear with new memory system
            logger.debug("Finish delete everything.")
        except Exception as e:
            logger.error(f"Error delete everything: {e}")
            return False
        return True

    def get_tools(self) -> list:
        return []
    
    async def show_env(self) -> list:
        env_list = Environment.get_all_environment()
        result = []
        for env in env_list:
            result.append([env.key, env.value[:10], env.description[:10]])
        return result

    async def remove_env(self, key: str) -> str:
        env = Environment.session.query(Environment).filter_by(key=key).first()
        if env is None:
            return f"Key {key} not found."
        Environment.session.delete(env)
        Environment.session.commit()
        return f"Key {key} removed successfully."
    
    async def add_env(self, key: str, value: str, description: str) -> str:
        env = Environment(key=key, value=value, description=description)
        Environment.session.add(env)
        Environment.session.commit()
        return f"Key {key} added successfully."
    
    async def excute_plan_task(self, task: dict) -> str:
        task_intance = str(task["function"]).split(".")
        if len(task_intance) < 2:
            return "Error: function name is not valid."
        class_name = task_intance[0]
        function_name = task_intance[1]
        task_func = getattr(self.skills_dict[class_name], function_name)
        logger.info(f"task_func: {task}")
        if "args" in task.keys():
            result = task_func(**task["args"])
        else:
            result = task_func()
        return result

    def excute_subtask(self, task: dict) -> str:
        task_intance = str(task["function"]).split(".")
        if len(task_intance) < 2:
            return "Error: function name is not valid."
        class_name = task_intance[0]
        function_name = task_intance[1]
        task_func = getattr(self.skills_dict[class_name], function_name)
        logger.info(f"task_func: {task}")
        if "args" in task.keys():
            result = task_func(**task["args"])
        else:
            result = task_func()
        return result

    def execute_plan(self, plan: dict) -> str:
        logger.info(f"execute plan: {plan}")
        tasks = plan.get("subtasks", [])
        result = ""
        for task in tasks:
            if task.get("function", "").startswith("unknow_"):
                continue
            result += str(self.excute_subtask(task))
        return result

    async def create_plan_and_running(self, goal_plan: str) -> str:
        # Create a new task for this plan
        task = Task.create_task(
            agent_id="agent",
            content=goal_plan,
            priority=0
        )
        
        # Execute the plan
        plan_json = await self.planning(goal=goal_plan)

        # replace ```json to empty string
        plan_json = plan_json.replace("```json", "").replace("```", "")
        plan_json = json.loads(plan_json)

        logger.info(f"plan_json: {plan_json}")
        tasks = plan_json.get("subtasks", [])

        result = ""
        for subtask in tasks:
            result += str(await self.excute_plan_task(subtask))
        
        # Mark task as completed
        task.complete({"result": result})
        return result

    async def create_schedule_for_task_or_plan(self, goal_plan: str) -> str:
        # TODO: Reimplement schedule creation with new brain system
        logger.warning("Schedule creation is temporarily disabled - brain system not implemented")
        return "Schedule creation is temporarily disabled - brain system not implemented"

    async def chat(self, input: str) -> str:
        """
        Process chat input using ReAct agent by default.
        Falls back to basic processing if ReAct is not available.
        
        Args:
            input: User input message
            
        Returns:
            Response string
        """
        try:
            # Always try to use ReAct agent first
            result = self.brain.process_query_with_react(input)
            
            # Extract response from ReAct result
            response = result.get('response', '')
            
            # Check for errors - if ReAct failed, fall back to basic processing
            if 'error' in result and 'LangChain not available' in result['error']:
                logger.info("ReAct agent not available, falling back to basic processing")
                result = self.brain.process_query(input)
                response = result.get('response', '')
                
                # If we found relevant skills, mention them
                relevant_skills = result.get('relevant_skills', [])
                if relevant_skills:
                    response += f"\n\nRelevant skills found: {', '.join(relevant_skills)}"
                    response += "\nYou can use these skills by calling them directly."
            elif 'error' in result:
                # Other ReAct errors - include in response but still return what we have
                response += f"\n\nNote: {result['error']}"
            
            # Log intermediate steps if available
            intermediate_steps = result.get('intermediate_steps', [])
            if intermediate_steps:
                logger.debug(f"ReAct agent took {len(intermediate_steps)} steps")
            
            return response
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"Error processing your message: {str(e)}"

    async def chat_code(self, input: str) -> str:
        # TODO: Reimplement chat_code with new memory and brain systems
        logger.warning("Chat code is temporarily disabled - memory and brain systems not implemented")
        return "Chat code is temporarily disabled - memory and brain systems not implemented"

    async def clear_short_term_memory(self) -> str:
        """Clear chat history from brain and start new conversation."""
        try:
            # Clear chat history using global conversation_id and start new conversation
            self.brain.clear_chat_history(start_new_conversation=True)
            return f"Chat history cleared successfully. New conversation started with ID: {self.brain.conversation_id}"
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            return f"Error clearing chat history: {str(e)}"

    async def ibelieve(self, input: str) -> bool:
        # maybe that gen by LLM + your input
        try:
            self.create_beslief(input, input)
            self.sync_beliefs()
            return True
        except Exception as e:
            logger.error(f"Error gen belief: {e}")
            return False

    async def askme(self, question: str) -> str:
        # TODO: Reimplement askme with new memory and brain systems
        logger.warning("Askme is temporarily disabled - memory and brain systems not implemented")
        return "Askme is temporarily disabled - memory and brain systems not implemented"

    async def reincarnate(self) -> str:
        if self.delete_everything():
            return "Reincarnate successfully."
        else:
            return "Reincarnate failed."

    async def planning(self, goal: str) -> str:
        # TODO: Reimplement planning with new memory and brain systems
        logger.warning("Planning is temporarily disabled - memory and brain systems not implemented")
        return "Planning is temporarily disabled - memory and brain systems not implemented"

    async def show_plan(self) -> str:
        # This method is now deprecated since we're using tasks instead of plans
        # We'll show pending tasks instead
        tasks = Task.get_pending_tasks()
        task_text = "Pending Tasks:\n"
        for task in tasks:
            task_text += f"- ID: {task.id}, Content: {task.content[:50]}..., Status: {task.status}, Priority: {task.priority}\n"
        return task_text

    async def show_schedule(self) -> str:
        schedule_jobs = ScheduleJob.get_all_schedule_not_completed_jobs()
        schedule_text = ""
        for job in schedule_jobs:
            schedule_text += "-----------------\n"
            schedule_text += f"**Task**: **{job.name}** \n"
            schedule_text += f"Description: {job.description}\n"
            schedule_text += f"Plan: {job.plan}\n"
            schedule_text += f"Recurrence: {job.is_recurring}\n\n"

        return schedule_text
