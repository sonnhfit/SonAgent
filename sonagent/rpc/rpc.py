"""
This module contains class to define a RPC communications
"""
import logging
from abc import abstractmethod
from typing import Any, Dict, Optional

from sonagent.rpc.rpc_types import RPCSendMsg
from sonagent.utils.utils import init_evironment

logger = logging.getLogger(__name__)


class RPCException(Exception):
    """
    Should be raised with a rpc-formatted message in an _rpc_* method
    if the required state is wrong, i.e.:

    raise RPCException('*Status:* `no active trade`')
    """

    def __init__(self, message: str) -> None:
        super().__init__(self)
        self.message = message

    def __str__(self):
        return self.message

    def __json__(self):
        return {
            'msg': self.message
        }


class RPCHandler:

    def __init__(self, rpc: 'RPC', config: dict) -> None:
        """
        Initializes RPCHandlers
        :param rpc: instance of RPC Helper class
        :param config: Configuration object
        :return: None
        """
        self._rpc = rpc
        self._config: dict = config

    @property
    def name(self) -> str:
        """ Returns the lowercase name of the implementation """
        return self.__class__.__name__.lower()

    @abstractmethod
    def cleanup(self) -> None:
        """ Cleanup pending module resources """

    @abstractmethod
    def send_msg(self, msg: RPCSendMsg) -> None:
        """ Sends a message to all registered rpc modules """


class RPC:
    def __init__(self, sonagent) -> None:
        """
        Initializes all enabled rpc modules
        :param freqtrade: Instance of a freqtrade bot
        :return: None
        """
        self.sonagent = sonagent
        self._config: dict = sonagent.config

    async def chat(self, msg: str) -> None:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        logger.info(f"[RPC] Processing chat message: {msg[:100]}...")
        try:
            result = await self.sonagent.chat(msg)
            logger.debug(f"[RPC] Chat result: {str(result)[:200]}...")
            logger.info(f"[RPC] Chat completed successfully")
            return result
        except Exception as e:
            logger.error(f"[RPC] Error in chat: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def confirm_action(self, run_id: str, confirm: bool, 
                           confirmation_note: Optional[str] = None) -> Dict[str, Any]:
        """
        Confirm or reject a paused action.
        
        Args:
            run_id: The run ID to continue
            confirm: Whether to confirm (True) or reject (False) the action
            confirmation_note: Optional note to provide when rejecting
            
        Returns:
            Dictionary with confirmation results
        """
        logger.info(f"[RPC] Confirming action for run {run_id}: confirm={confirm}")
        try:
            # Check if team agent is available
            if not hasattr(self.sonagent, 'team_agent') or not self.sonagent.team_agent:
                return {
                    "success": False,
                    "error": "Team agent not initialized",
                    "message": "Please ensure team agent is properly initialized"
                }
            
            # Handle confirmation
            result = await self.sonagent.team_agent.handle_confirmation(
                run_id=run_id,
                confirm=confirm,
                confirmation_note=confirmation_note
            )
            
            logger.info(f"[RPC] Confirmation handled: success={result.get('success')}")
            return result
            
        except Exception as e:
            logger.error(f"[RPC] Error confirming action: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to confirm action"
            }
    
    async def ibelieve(self, msg: str) -> bool:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        is_belief_added = await self.sonagent.ibelieve(msg)
        if is_belief_added:
            return "Belief added"
    
        return "Belief not added"

    async def reincarnate(self) -> None:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.reincarnate()
    
    async def show_env(self) -> list:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.show_env()
    
    async def add_env(self, key: str, value: str, description: str) -> str:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.add_env(key, value, description)
    
    async def remove_env(self, key: str) -> str:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.remove_env(key)
    
    async def reload_env(self) -> str:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        init_evironment()
        return "Env reloaded"
    
    async def clear_short_term_memory(self) -> str:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.clear_short_term_memory()
    
    async def show_task(self) -> str:
        """
        Show all tasks with detailed information using the Task model.
        Similar to show_plan but shows all tasks with more details.
        """
        return await self.sonagent.show_task()
    
    async def show_skills(self) -> str:
        return self.sonagent.show_skills()
    
    async def show_schedule(self) -> str:
        return await self.sonagent.show_schedule()
    
    async def reload_skills(self) -> str:
        return self.sonagent.reload_skills()
    
    async def remove_skill(self, skill_name: str) -> str:
        return await self.sonagent.remove_skill(skill_name)
    
    async def summerize_dialog(self) -> str:
        return self.sonagent.agent.short_term_memory.summerize_dialog()
    
    # Team agent methods
    async def create_task(self, content: str, priority: int = 0) -> str:
        """
        Create a task using team agent.
        
        Args:
            content: Task description
            priority: Task priority
            
        Returns:
            Task creation result
        """
        logger.info(f"[RPC] Creating task: {content[:50]}...")
        try:
            result = await self.sonagent.create_task_via_team(content, priority)
            logger.info(f"[RPC] Task creation completed")
            return result
        except Exception as e:
            logger.error(f"[RPC] Error creating task: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def get_tasks(self, status: str = None, limit: int = 10) -> str:
        """
        Get tasks using team agent.
        
        Args:
            status: Filter by task status
            limit: Maximum number of tasks
            
        Returns:
            Task list
        """
        logger.info(f"[RPC] Getting tasks, status={status}, limit={limit}")
        try:
            result = await self.sonagent.get_tasks_via_team(status, limit)
            logger.info(f"[RPC] Task retrieval completed")
            return result
        except Exception as e:
            logger.error(f"[RPC] Error getting tasks: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def update_task(self, task_id: int, status: str, result_data: str = None) -> str:
        """
        Update a task using team agent.
        
        Args:
            task_id: Task ID
            status: New status
            result_data: Task result data (JSON string)
            
        Returns:
            Update result
        """
        logger.info(f"[RPC] Updating task {task_id} to status {status}")
        try:
            import json
            result_dict = json.loads(result_data) if result_data else None
            result = await self.sonagent.update_task_via_team(task_id, status, result_dict)
            logger.info(f"[RPC] Task update completed")
            return result
        except Exception as e:
            logger.error(f"[RPC] Error updating task: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def get_chat_history(self, conversation_id: str = None, limit: int = 20) -> str:
        """
        Get chat history using team agent.
        
        Args:
            conversation_id: Conversation ID (uses current if None)
            limit: Maximum number of messages
            
        Returns:
            Chat history
        """
        logger.info(f"[RPC] Getting chat history, conversation_id={conversation_id}, limit={limit}")
        try:
            result = await self.sonagent.get_chat_history_via_team(conversation_id, limit)
            logger.info(f"[RPC] Chat history retrieval completed")
            return result
        except Exception as e:
            logger.error(f"[RPC] Error getting chat history: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def extract_tom(self, conversation_text: str, user_id: str = "default") -> str:
        """
        Extract Theory of Mind using team agent.
        
        Args:
            conversation_text: Conversation text to analyze
            user_id: User identifier
            
        Returns:
            TOM analysis result
        """
        logger.info(f"[RPC] Extracting TOM for user {user_id}")
        try:
            result = await self.sonagent.extract_tom_via_team(conversation_text, user_id)
            logger.info(f"[RPC] TOM extraction completed")
            return result
        except Exception as e:
            logger.error(f"[RPC] Error extracting TOM: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def request_feedback(self, action: str, context: str) -> str:
        """
        Request human feedback using team agent.
        
        Args:
            action: The action requiring feedback
            context: Context about why feedback is needed
            
        Returns:
            Feedback request message
        """
        logger.info(f"[RPC] Requesting feedback for action: {action}")
        try:
            result = await self.sonagent.request_feedback_via_team(action, context)
            logger.info(f"[RPC] Feedback request completed")
            return result
        except Exception as e:
            logger.error(f"[RPC] Error requesting feedback: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def get_team_agent_info(self) -> dict:
        """
        Get information about the team agent.
        
        Returns:
            Team agent information
        """
        logger.info(f"[RPC] Getting team agent info")
        try:
            result = self.sonagent.get_team_agent_info()
            logger.info(f"[RPC] Team agent info retrieval completed")
            return result
        except Exception as e:
            logger.error(f"[RPC] Error getting team agent info: {e}", exc_info=True)
            return {"error": str(e), "message": "Failed to get team agent info"}
