"""
Base Agent class for all agents in the SonAgent system.
All agents inherit from this base class.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from sonagent.brain import AgentBrain
from sonagent.skills.skills_manager import SkillsManager
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    Provides common functionality for agent operations.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        config: Dict[str, Any],
        skills_manager: SkillsManager,
        agent_registry: Any = None
    ):
        """
        Initialize base agent.
        
        Args:
            agent_id: Unique identifier for this agent
            agent_name: Human-readable name for this agent
            config: Configuration dictionary
            skills_manager: SkillsManager instance
            agent_registry: AgentRegistry instance for inter-agent communication
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.config = config
        self.skills_manager = skills_manager
        self.agent_registry = agent_registry
        self.created_at = dt_now()
        self.status = "initialized"
        
        # Initialize brain with agent-specific conversation ID
        conversation_id = f"{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.brain = AgentBrain(
            config=config,
            skills_manager=skills_manager,
            conversation_id=conversation_id
        )
        
        logger.info(f"Initialized {self.agent_name} (ID: {self.agent_id})")
        
        # Register with agent registry if available
        if self.agent_registry:
            self.agent_registry.register_agent(self)
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """
        Process input data and return result.
        Must be implemented by subclasses.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processing result
        """
        pass
    
    @abstractmethod
    async def run_continuous(self) -> None:
        """
        Run continuous background tasks.
        Must be implemented by subclasses.
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status.
        
        Returns:
            Status dictionary
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "skills_loaded": len(self.skills_manager.get_all_skills())
        }
    
    def update_status(self, status: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Update agent status and notify registry.
        
        Args:
            status: New status string
            data: Optional additional data
        """
        self.status = status
        if self.agent_registry:
            self.agent_registry.update_agent_status(
                self.agent_id,
                status,
                data or {}
            )
        logger.debug(f"Agent {self.agent_id} status updated to: {status}")
    
    async def chat(self, input: str) -> str:
        """
        Process chat input using agent's brain.
        
        Args:
            input: User input message
            
        Returns:
            Response string
        """
        try:
            result = self.brain.process_query_with_react(input)
            response = result.get('response', '')
            
            if 'error' in result and 'LangChain not available' in result['error']:
                logger.info("ReAct agent not available, falling back to basic processing")
                result = self.brain.process_query(input)
                response = result.get('response', '')
            elif 'error' in result:
                response += f"\n\nNote: {result['error']}"
            
            return response
        except Exception as e:
            logger.error(f"Error in chat for agent {self.agent_id}: {e}")
            return f"Error processing your message: {str(e)}"
    
    def reload_skills(self) -> None:
        """Reload skills for this agent."""
        logger.info(f"Reloading skills for agent {self.agent_id}")
        self.skills_manager.reload_skills()
        self.brain.load_and_index_skills()
