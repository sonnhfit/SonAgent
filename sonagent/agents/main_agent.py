"""
Main Agent - Coordinates all other agents in the system.
Handles user communication, task creation, and task management.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from sonagent.agents.base_agent import BaseAgent
from sonagent.persistence import Task
from sonagent.skills.skills_manager import SkillsManager

logger = logging.getLogger(__name__)


class MainAgent(BaseAgent):
    """
    Main Agent that coordinates all sub-agents.
    
    Responsibilities:
    - Communicate with users (Q&A)
    - Create and manage tasks
    - Monitor sub-agent status
    - Coordinate task execution across agents
    - Kill/stop tasks when needed
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        skills_manager: SkillsManager,
        agent_registry: Any = None
    ):
        """
        Initialize the main agent.
        
        Args:
            config: Configuration dictionary
            skills_manager: SkillsManager instance
            agent_registry: AgentRegistry instance for inter-agent communication
        """
        super().__init__(
            agent_id="main_agent",
            agent_name="Main Agent",
            config=config,
            skills_manager=skills_manager,
            agent_registry=agent_registry
        )
        
        # Task management
        self.active_tasks = {}  # task_id -> task info
        self.running = False
        
        logger.info("Main Agent initialized successfully")
    
    async def process(self, input_data: Any) -> Any:
        """
        Process user input/commands.
        
        Args:
            input_data: User input (string or dict)
            
        Returns:
            Processing result
        """
        try:
            # Handle different input types
            if isinstance(input_data, str):
                return await self._process_chat(input_data)
            elif isinstance(input_data, dict):
                command = input_data.get('command')
                if command == 'create_task':
                    return await self._create_task(input_data)
                elif command == 'list_tasks':
                    return await self._list_tasks()
                elif command == 'get_task_status':
                    return await self._get_task_status(input_data.get('task_id'))
                elif command == 'kill_task':
                    return await self._kill_task(input_data.get('task_id'))
                elif command == 'list_agents':
                    return await self._list_agents()
                else:
                    return f"Unknown command: {command}"
            else:
                return "Invalid input format"
        except Exception as e:
            logger.error(f"Error processing input in MainAgent: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def _process_chat(self, message: str) -> str:
        """
        Process chat message from user.
        
        Args:
            message: User message
            
        Returns:
            Response string
        """
        # Use parent class chat method
        return await self.chat(message)
    
    async def _create_task(self, task_data: Dict[str, Any]) -> str:
        """
        Create a new task.
        
        Args:
            task_data: Task data dictionary with 'content', 'priority', etc.
            
        Returns:
            Task creation result
        """
        try:
            content = task_data.get('content', '')
            priority = task_data.get('priority', 0)
            agent_id = task_data.get('agent_id', 'main_agent')
            
            task = Task.create_task(
                agent_id=agent_id,
                content=content,
                priority=priority
            )
            
            self.active_tasks[task.id] = {
                'task': task,
                'agent_id': agent_id,
                'status': 'pending'
            }
            
            logger.info(f"Created task {task.id} for agent {agent_id}")
            return f"Task created successfully. Task ID: {task.id}"
        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            return f"Failed to create task: {str(e)}"
    
    async def _list_tasks(self) -> str:
        """
        List all tasks.
        
        Returns:
            String with task list
        """
        try:
            pending_tasks = Task.get_pending_tasks()
            completed_tasks = Task.get_completed_tasks()
            
            result = "**Pending Tasks:**\n"
            for task in pending_tasks:
                result += f"- ID: {task.id}, Agent: {task.agent_id}, Priority: {task.priority}\n"
                result += f"  Content: {task.content[:50]}...\n"
            
            result += "\n**Completed Tasks:**\n"
            for task in completed_tasks[:5]:  # Show last 5 completed
                result += f"- ID: {task.id}, Agent: {task.agent_id}\n"
                result += f"  Content: {task.content[:50]}...\n"
            
            return result
        except Exception as e:
            logger.error(f"Error listing tasks: {e}", exc_info=True)
            return f"Failed to list tasks: {str(e)}"
    
    async def _get_task_status(self, task_id: int) -> str:
        """
        Get status of a specific task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status string
        """
        try:
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                task = task_info['task']
                return f"Task {task_id}: {task.status} (Agent: {task_info['agent_id']})"
            else:
                return f"Task {task_id} not found in active tasks"
        except Exception as e:
            logger.error(f"Error getting task status: {e}", exc_info=True)
            return f"Failed to get task status: {str(e)}"
    
    async def _kill_task(self, task_id: int) -> str:
        """
        Kill/cancel a running task.
        
        Args:
            task_id: Task ID to kill
            
        Returns:
            Kill result string
        """
        try:
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                task = task_info['task']
                
                # Mark task as cancelled
                task.status = 'cancelled'
                Task.session.commit()
                
                # Remove from active tasks
                del self.active_tasks[task_id]
                
                logger.info(f"Killed task {task_id}")
                return f"Task {task_id} has been cancelled"
            else:
                return f"Task {task_id} not found in active tasks"
        except Exception as e:
            logger.error(f"Error killing task: {e}", exc_info=True)
            return f"Failed to kill task: {str(e)}"
    
    async def _list_agents(self) -> str:
        """
        List all registered agents.
        
        Returns:
            String with agent list
        """
        try:
            if not self.agent_registry:
                return "Agent registry not available"
            
            agents = self.agent_registry.get_all_agents()
            result = "**Registered Agents:**\n"
            for agent_id, agent_info in agents.items():
                result += f"- {agent_id}: {agent_info.get('agent_name', 'Unknown')}\n"
                result += f"  Status: {agent_info.get('status', 'Unknown')}\n"
            
            return result
        except Exception as e:
            logger.error(f"Error listing agents: {e}", exc_info=True)
            return f"Failed to list agents: {str(e)}"
    
    async def run_continuous(self) -> None:
        """
        Run continuous background tasks for the main agent.
        
        This includes:
        - Monitoring task queue
        - Checking agent health
        - Auto-improvement cycles
        """
        self.running = True
        logger.info("Main Agent continuous loop started")
        
        while self.running:
            try:
                # Monitor pending tasks
                await self._monitor_tasks()
                
                # Check agent health
                if self.agent_registry:
                    await self._check_agent_health()
                
                # Sleep before next iteration
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in main agent continuous loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Shorter sleep on error
    
    async def _monitor_tasks(self) -> None:
        """Monitor and process pending tasks."""
        try:
            pending_tasks = Task.get_pending_tasks()
            
            for task in pending_tasks:
                if task.id not in self.active_tasks:
                    # New task - add to active tasks
                    self.active_tasks[task.id] = {
                        'task': task,
                        'agent_id': task.agent_id,
                        'status': 'pending'
                    }
                    logger.info(f"New task detected: {task.id}")
        except Exception as e:
            logger.error(f"Error monitoring tasks: {e}", exc_info=True)
    
    async def _check_agent_health(self) -> None:
        """Check health of all registered agents."""
        try:
            agents = self.agent_registry.get_all_agents()
            for agent_id, agent_info in agents.items():
                # Log agent status for monitoring
                logger.debug(f"Agent {agent_id} status: {agent_info.get('status')}")
        except Exception as e:
            logger.error(f"Error checking agent health: {e}", exc_info=True)
    
    def stop(self) -> None:
        """Stop the main agent's continuous loop."""
        self.running = False
        logger.info("Main Agent stopped")
