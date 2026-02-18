import json
import logging
import os
from datetime import datetime
from pathlib import Path

import yaml
from croniter import croniter
from tabulate import tabulate

from sonagent.persistence import Belief, Environment, Task
from sonagent.tools import GitManager, LocalCodeManager
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, memory_path, skills, config: dict, conversation_id: str = None) -> None:
        self.config = config

        logger.debug(f"Init memory with path {memory_path}.")
        
        # Store conversation_id for reference
        self.conversation_id = conversation_id or self._generate_conversation_id()
        logger.debug(f"Agent initialized with conversation_id: {self.conversation_id}")
        
        # Keep skills for backward compatibility
        self.skills = skills
        self.skills_dict = {}
        
        # Main agent is no longer used - chat functionality is handled by MainTeamAgent
        self.main_agent = None
        logger.info("Main agent initialization skipped (using MainTeamAgent instead)")
        
        # Store sub-agents
        self.sub_agents = {}

        logger.info("--------- Start skill.---------")
        # Load skills
        self.skills.reload_skills()
        self.init_skills_dict()
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
        # Reload skills
        self.skills.reload_skills()
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

    async def create_schedule_for_task_or_plan(self, goal_plan: str) -> str:
        # TODO: Reimplement schedule creation with new brain system
        logger.warning("Schedule creation is temporarily disabled - brain system not implemented")
        return "Schedule creation is temporarily disabled - brain system not implemented"

    async def chat(self, input: str) -> str:
        """
        Process chat input.
        
        Args:
            input: User input message
            
        Returns:
            Response string
        """
        try:
            # MainAgent is no longer used - chat is handled by MainTeamAgent in sonbot.py
            # This is a fallback implementation for when team agent is not available
            logger.warning("Using fallback chat implementation - MainTeamAgent should handle chat")
            return f"I received your message: '{input}'. Chat functionality is now handled by the team agent system. Please ensure MainTeamAgent is initialized."
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"Error processing your message: {str(e)}"

    async def chat_code(self, input: str) -> str:
        # TODO: Reimplement chat_code with new memory and brain systems
        logger.warning("Chat code is temporarily disabled - memory and brain systems not implemented")
        return "Chat code is temporarily disabled - memory and brain systems not implemented"

    async def clear_short_term_memory(self) -> str:
        """Clear chat history and start new conversation."""
        try:
            # Generate new conversation ID
            old_id = self.conversation_id
            self.conversation_id = self._generate_conversation_id()
            logger.info(f"Cleared chat history and started new conversation: {old_id} -> {self.conversation_id}")
            return f"Chat history cleared successfully. New conversation started with ID: {self.conversation_id}"
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

    async def reincarnate(self) -> str:
        if self.delete_everything():
            return "Reincarnate successfully."
        else:
            return "Reincarnate failed."

    async def show_task(self) -> str:
        """
        Show all tasks with detailed information using the Task model.
        Similar to show_plan but shows all tasks with more details.
        """
        all_tasks = Task.get_all_tasks()
        
        if not all_tasks:
            return "📭 *No tasks found.*"
        
        # Define status emojis
        status_emojis = {
            'pending': '⏳',
            'in_progress': '⚙️',
            'done': '✅',
            'failed': '❌',
            'cancelled': '🚫'
        }
        
        # Prepare table data with only ID, Content, Status
        table_data = []
        for task in all_tasks:
            # Get status emoji
            emoji = status_emojis.get(task.status, '📝')
            
            # Format content (truncate)
            content = task.content[:50] + ('...' if len(task.content) > 50 else '')
            
            # Add to table
            table_data.append([
                f"{emoji} #{task.id}",
                content,
                task.status.replace('_', ' ').title()
            ])
        
        # Create table
        headers = ["ID", "Content", "Status"]
        table = tabulate(table_data, headers=headers, tablefmt="simple")
        
        # Add summary
        total_tasks = len(all_tasks)
        pending = len([t for t in all_tasks if t.status == 'pending'])
        in_progress = len([t for t in all_tasks if t.status == 'in_progress'])
        done = len([t for t in all_tasks if t.status == 'done'])
        failed = len([t for t in all_tasks if t.status == 'failed'])
        cancelled = len([t for t in all_tasks if t.status == 'cancelled'])
        
        summary_table = [
            ["Total", total_tasks],
            ["In Progress", in_progress],
            ["Pending", pending],
            ["Completed", done],
            ["Failed", failed],
            ["Cancelled", cancelled]
        ]
        
        summary = tabulate(summary_table, headers=["Status", "Count"], tablefmt="simple")
        
        # Calculate completion rate
        completion_rate = (done / total_tasks * 100) if total_tasks > 0 else 0
        
        # Build final message
        from datetime import datetime
        message = (
            f"📋 *Task Overview*\n"
            f"═══════════════════════\n\n"
            f"```\n{table}\n```\n\n"
            f"📊 *Task Summary*\n"
            f"═══════════════════════\n\n"
            f"```\n{summary}\n```\n\n"
            f"📈 *Completion Rate:* `{completion_rate:.1f}%`\n"
            f"🕒 *Last Updated:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        
        return message

    def _generate_conversation_id(self) -> str:
        """
        Generate a unique conversation ID.
        
        Returns:
            Unique conversation ID string
        """
        import time
        import uuid

        # Generate a UUID and combine with timestamp for uniqueness
        unique_id = str(uuid.uuid4())[:8]
        timestamp = int(time.time())
        return f"conv_{timestamp}_{unique_id}"
