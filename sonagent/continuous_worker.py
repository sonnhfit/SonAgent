"""
Continuous Task Worker - Runs background tasks for agents.

This module provides a worker that can run continuous tasks for agents,
including self-improvement loops, task monitoring, and periodic maintenance.
"""
import asyncio
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from sonagent.agent_registry import AgentRegistry
from sonagent.agents.base_agent import BaseAgent
from sonagent.persistence import Task
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class ContinuousTaskWorker:
    """
    Worker that runs continuous background tasks for agents.
    
    Features:
    - Run agent continuous loops in background
    - Monitor task queue
    - Execute scheduled tasks
    - Agent self-improvement cycles
    - Periodic skill reloading
    """
    
    def __init__(self, agent_registry: AgentRegistry):
        """
        Initialize the continuous task worker.
        
        Args:
            agent_registry: Agent registry instance
        """
        self.agent_registry = agent_registry
        self.running = False
        self.worker_thread = None
        self.tasks = {}  # task_id -> asyncio.Task
        
        logger.info("Continuous Task Worker initialized")
    
    def start(self) -> None:
        """Start the continuous task worker in a background thread."""
        if self.running:
            logger.warning("Continuous task worker is already running")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self.worker_thread.start()
        logger.info("Continuous task worker started")
    
    def stop(self) -> None:
        """Stop the continuous task worker."""
        if not self.running:
            return
        
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Continuous task worker stopped")
    
    def _run_worker(self) -> None:
        """Main worker loop (runs in background thread)."""
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._async_worker_loop())
        except Exception as e:
            logger.error(f"Error in continuous task worker: {e}", exc_info=True)
        finally:
            loop.close()
    
    async def _async_worker_loop(self) -> None:
        """Async worker loop."""
        logger.info("Starting async worker loop")
        
        while self.running:
            try:
                # Monitor pending tasks
                await self._monitor_pending_tasks()
                
                # Run agent continuous tasks
                await self._run_agent_continuous_tasks()
                
                # Periodic maintenance
                await self._periodic_maintenance()
                
                # Sleep before next iteration
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Short sleep on error
    
    async def _monitor_pending_tasks(self) -> None:
        """Monitor and execute pending tasks."""
        try:
            pending_tasks = Task.get_pending_tasks()
            
            for task in pending_tasks:
                if task.id not in self.tasks:
                    # New task - start execution
                    logger.info(f"Starting execution of task {task.id}")
                    asyncio_task = asyncio.create_task(self._execute_task(task))
                    self.tasks[task.id] = asyncio_task
        except Exception as e:
            logger.error(f"Error monitoring pending tasks: {e}", exc_info=True)
    
    async def _execute_task(self, task: Task) -> None:
        """
        Execute a task.
        
        Args:
            task: Task to execute
        """
        try:
            logger.info(f"Executing task {task.id} for agent {task.agent_id}")
            
            # Get the agent from registry
            agent_info = self.agent_registry.get_agent_status(task.agent_id)
            if not agent_info:
                logger.warning(f"Agent {task.agent_id} not found in registry")
                task.status = 'failed'
                Task.session.commit()
                return
            
            # Update task status
            task.status = 'running'
            Task.session.commit()
            
            # Get agent instance
            agents = self.agent_registry.get_all_agents()
            if task.agent_id not in agents:
                logger.warning(f"Agent instance for {task.agent_id} not found")
                task.status = 'failed'
                Task.session.commit()
                return
            
            agent = agents[task.agent_id].get('agent')
            if not agent:
                logger.warning(f"Agent instance for {task.agent_id} is None")
                task.status = 'failed'
                Task.session.commit()
                return
            
            # Process task with agent
            result = await agent.process(task.content)
            
            # Mark task as completed
            task.complete({'result': result})
            logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {e}", exc_info=True)
            task.status = 'failed'
            Task.session.commit()
        finally:
            # Remove from active tasks
            if task.id in self.tasks:
                del self.tasks[task.id]
    
    async def _run_agent_continuous_tasks(self) -> None:
        """Run continuous tasks for all agents."""
        try:
            agents = self.agent_registry.get_all_agents()
            
            for agent_id, agent_info in agents.items():
                agent = agent_info.get('agent')
                if agent and hasattr(agent, 'run_continuous'):
                    # Check if agent's continuous task is already running
                    continuous_task_id = f"continuous_{agent_id}"
                    if continuous_task_id not in self.tasks:
                        # Start agent's continuous task
                        asyncio_task = asyncio.create_task(agent.run_continuous())
                        self.tasks[continuous_task_id] = asyncio_task
                        logger.info(f"Started continuous task for agent {agent_id}")
        except Exception as e:
            logger.error(f"Error running agent continuous tasks: {e}", exc_info=True)
    
    async def _periodic_maintenance(self) -> None:
        """Perform periodic maintenance tasks."""
        try:
            # Clear old messages from registry
            if hasattr(self, '_last_cleanup'):
                time_since_cleanup = (dt_now() - self._last_cleanup).total_seconds()
                if time_since_cleanup > 3600:  # Cleanup every hour
                    self.agent_registry.clear_old_messages(days=7)
                    self._last_cleanup = dt_now()
            else:
                self._last_cleanup = dt_now()
            
            # Reload skills periodically for all agents
            agents = self.agent_registry.get_all_agents()
            for agent_id, agent_info in agents.items():
                agent = agent_info.get('agent')
                if agent and hasattr(agent, 'skills_manager'):
                    # Check if skills need reloading
                    if hasattr(agent.skills_manager, 'periodic_scan_and_reload'):
                        reloaded = agent.skills_manager.periodic_scan_and_reload()
                        if reloaded:
                            logger.info(f"Skills reloaded for agent {agent_id}")
                            # Update agent brain if skills were reloaded
                            if hasattr(agent, 'brain'):
                                agent.brain.load_and_index_skills()
        except Exception as e:
            logger.error(f"Error in periodic maintenance: {e}", exc_info=True)


# Global worker instance
_worker_instance: Optional[ContinuousTaskWorker] = None


def start_continuous_worker(agent_registry: AgentRegistry) -> ContinuousTaskWorker:
    """
    Start the global continuous task worker.
    
    Args:
        agent_registry: Agent registry instance
        
    Returns:
        Worker instance
    """
    global _worker_instance
    
    if _worker_instance is None:
        _worker_instance = ContinuousTaskWorker(agent_registry)
    
    _worker_instance.start()
    return _worker_instance


def stop_continuous_worker() -> None:
    """Stop the global continuous task worker."""
    global _worker_instance
    
    if _worker_instance:
        _worker_instance.stop()
        _worker_instance = None


def get_continuous_worker() -> Optional[ContinuousTaskWorker]:
    """
    Get the global continuous task worker instance.
    
    Returns:
        Worker instance or None
    """
    return _worker_instance
