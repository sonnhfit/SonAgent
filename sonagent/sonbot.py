import ast
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from typing import Any, Dict, Optional

from croniter import croniter
from schedule import Scheduler

from sonagent.agent import Agent
from sonagent.agents import MainTeamAgent
from sonagent.enums.enums import State
from sonagent.enums.rpcmessagetype import RPCMessageType
from sonagent.loggers.logging_mixin import LoggingMixin
from sonagent.persistence.models import init_db
from sonagent.rpc import IOMsg, RPCManager
from sonagent.skills.skills_manager import SkillsManager
from sonagent.tools.tool_registry import ToolRegistry
from sonagent.utils.datetime_helpers import dt_now
from sonagent.utils.utils import init_evironment

# import threading


logger = logging.getLogger(__name__)


class SonBot(LoggingMixin):
    def __init__(self, config: dict, args: Any = None) -> None:

        self.state = State.STOPPED
        
        self.args = args
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        self.config = config
        
        # Global conversation ID for consistent chat context
        # Generate a new conversation ID on startup
        self.conversation_id = self._generate_conversation_id()
        
        logger.info(f"SonBot initialized with conversation_id: {self.conversation_id}")
        
        memory_url = self.args.get('memory-url', "user_data/memory")
        agentdb = self.args.get('agentdb', "sqlite:///user_data/agentdb.db")

        llm = self.config.get('llm')
        if llm.get('api_type', None) == 'openai':
            os.environ["OPENAI_API_KEY"] = llm.get('api_key')
            logger.info("Run with openai LLM")

        if agentdb is None:
            agentdb = "sqlite:///user_data/agentdb.db"
        
        if memory_url is None:
            memory_url = "./user_data/memory"

        try:
            init_db(agentdb)
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise e

        # Initialize MainTeamAgent for team-based processing
        self.team_agent = None
        self._init_team_agent()

        # Initialize WorkerTeamAgent for task prioritization and execution
        self.worker_team_agent = None
        self._init_worker_team_agent()

        # init env 
        init_evironment()

        self.skills = SkillsManager(self)

        # Initialize ToolRegistry for dynamic tool loading
        self.tool_registry = ToolRegistry(self.config)

        names = str(self.skills.load_register_skills_name())
        self._schedule = Scheduler()

        # Initialize task queue for agent worker
        self.task_queue = Queue()

        # Pass conversation_id to Agent
        self.agent = Agent(
            memory_path=memory_url, 
            skills=self.skills, 
            config=self.config,
            conversation_id=self.conversation_id
        )
        
        
        self.rpc: RPCManager = RPCManager(self)

        # Add skill scanning every 10 seconds
        def scan_skills():
            self.scan_and_reload_skills()

        # Add tool scanning every 30 seconds (matching ToolRegistry scan interval)
        def scan_tools():
            self.scan_and_reload_tools()

        def agent_worker_cronjob_schedule():
            self.scan_task_for_agent_worker()

        def agent_worker_task_execute():
            self.execute_task_from_queue()
        
        self._schedule.every(10).seconds.do(scan_skills)
        self._schedule.every(30).seconds.do(scan_tools)
        self._schedule.every(11).seconds.do(agent_worker_cronjob_schedule)
        self._schedule.every(60).seconds.do(agent_worker_task_execute)

        # Set initial bot state from config
        initial_state = self.config.get('initial_state')

        self.state = State[initial_state.upper()] if initial_state else State.STOPPED
        
        IOMsg.rpc = self.rpc
        self.last_skill_scan_time = 0
        self.cached_skill_files = set()
    
    def _init_team_agent(self) -> None:
        """
        Initialize the MainTeamAgent.
        """
        try:
            # Use the same database as the main agent (agentdb.sqlite)
            # Get the database URL from args or use default
            agentdb = self.args.get('agentdb') if self.args else None
            if not agentdb:
                agentdb = "sqlite:///user_data/agentdb.db"
                logger.info(f"Using default agentdb: {agentdb}")
            
            # Extract the file path from the URL for MainTeamAgent
            # sqlite:///user_data/agentdb.sqlite -> user_data/agentdb.sqlite
            # if agentdb.startswith('sqlite:///'):
            #     db_path = agentdb.replace('sqlite:///', '')
            # else:
                # Fallback to default path
            user_data_dir = self.config.get('user_data_dir', 'user_data')
            db_path = f"{user_data_dir}/agentdb.db"
            
            # Get memory URL for ChromaDB path
            memory_url = self.args.get('memory-url', "user_data/memory")

            # Clear team registry on startup using utility function
            try:
                from sonagent.utils.utils import init_team_registry
                init_team_registry(agentdb)
            except Exception as reg_error:
                logger.warning(f"Could not clear team registry on startup: {reg_error}")
                
            self.team_agent = MainTeamAgent(
                config=self.config,
                db_path=db_path,
                memory_db_path=memory_url
            )
            logger.info(f"MainTeamAgent initialized successfully with db_path: {db_path}, memory_db_path: {memory_url}")
            
            # Register the team in the registry using utility function
            try:
                from sonagent.utils.utils import register_team_in_registry
                from sonagent.utils.datetime_helpers import dt_now
                
                # Register the main team
                result = register_team_in_registry(
                    team_name="Main Team",
                    description="Main team agent coordinating multiple specialized agents for handling user requests via RPC with human feedback integration and persistent chat history.",
                    db_url=agentdb,
                    config={
                        "team_type": "main",
                        "agent_count": 4,  # assistant, task, tom, feedback agents
                        "mode": "coordinate"
                    },
                    team_metadata={
                        "initialized_at": dt_now().isoformat(),
                        "conversation_id": self.conversation_id
                    }
                )
                
                if result.get("success"):
                    logger.info(f"Registered team in registry: {result.get('team_name')}")
                else:
                    logger.warning(f"Could not register team in registry: {result.get('error')}")
                    
            except Exception as reg_error:
                logger.warning(f"Could not register team in registry: {reg_error}")
                
        except Exception as e:
            logger.error(f"Failed to initialize MainTeamAgent: {e}")
            self.team_agent = None
    
    def _init_worker_team_agent(self) -> None:
        """
        Initialize the WorkerTeamAgent.
        """
        try:
            # Use the same database as the main agent (agentdb.sqlite)
            # Get the database URL from args or use default
            agentdb = self.args.get('agentdb') if self.args else None
            if not agentdb:
                agentdb = "sqlite:///user_data/agentdb.db"
                logger.info(f"Using default agentdb for worker team: {agentdb}")
            
            # Extract the file path from the URL for WorkerTeamAgent
            user_data_dir = self.config.get('user_data_dir', 'user_data')
            db_path = f"{user_data_dir}/agentdb.db"
            
            # Get memory URL for ChromaDB path
            memory_url = self.args.get('memory-url', "user_data/memory")

            # Import WorkerTeamAgent
            from sonagent.agents.worker_team import WorkerTeamAgent
                
            self.worker_team_agent = WorkerTeamAgent(
                config=self.config,
                db_path=db_path,
                memory_db_path=memory_url
            )
            logger.info(f"WorkerTeamAgent initialized successfully with db_path: {db_path}, memory_db_path: {memory_url}")
            
            # Register the worker team in the registry using utility function
            try:
                from sonagent.utils.utils import register_team_in_registry
                from sonagent.utils.datetime_helpers import dt_now
                
                # Register the worker team
                result = register_team_in_registry(
                    team_name="Worker Team",
                    description="Worker team agent for task prioritization and execution considering short-term and long-term goals with token usage tracking.",
                    db_url=agentdb,
                    config={
                        "team_type": "worker",
                        "agent_count": 1,  # worker agent
                        "mode": "single_agent",
                        "tools": ["get_task_list_tool", "get_targets_tool", "update_task_execution_data_tool"]
                    },
                    team_metadata={
                        "initialized_at": dt_now().isoformat(),
                        "conversation_id": self.conversation_id,
                        "purpose": "task_prioritization_and_execution"
                    }
                )
                
                if result.get("success"):
                    logger.info(f"Registered worker team in registry: {result.get('team_name')}")
                else:
                    logger.warning(f"Could not register worker team in registry: {result.get('error')}")
                    
            except Exception as reg_error:
                logger.warning(f"Could not register worker team in registry: {reg_error}")
                
        except Exception as e:
            logger.error(f"Failed to initialize WorkerTeamAgent: {e}")
            self.worker_team_agent = None


    def scan_task_for_agent_worker(self) -> None:
        """
        Scan tasks from database and push eligible tasks to the queue.
        This function is called every 11 seconds by the scheduler.
        
        It will:
        1. Get all tasks with status 'pending'
        2. Check tasks with cron_expression if they match current time (within 10-60s window)
        3. Check tasks with scheduled_at if they match current time at minute level
        4. If task is not already in queue, push it to queue
        5. Update task status to 'in_progress' atomically
        
        For periodic tasks with cron expressions, they will be reset to 'pending' after execution
        so they can be scanned again for the next scheduled run.
        For tasks with scheduled_at (one-time scheduled tasks), they will be marked as done/failed after execution.
        """
        try:
            from sonagent.persistence import Task
            from croniter import croniter
            
            # Get current time
            current_time = dt_now()
            
            # Get all pending tasks
            pending_tasks = Task.get_tasks_by_status('pending')
            logger.debug(f"Scanning {len(pending_tasks)} pending tasks")
            
            tasks_added = 0
            for task in pending_tasks:
                task_added = False
                
                # Check tasks with cron expression (periodic tasks)
                if task.cron_expression:
                    try:
                        # Create cron iterator based on task's scheduled_at or created_at
                        base_time = task.scheduled_at or task.created_at
                        if croniter.is_valid(task.cron_expression):
                            cron = croniter(task.cron_expression, base_time)
                            next_time = cron.get_next(datetime)
                            
                            # Make next_time timezone-aware (UTC) to match current_time
                            # croniter returns naive datetime, but current_time is timezone-aware
                            if next_time.tzinfo is None:
                                next_time = next_time.replace(tzinfo=timezone.utc)
                            
                            # Check if current time is within 10-60 seconds of next execution time
                            # This matches the requirement "có thể lệnh khoảng 10-60s"
                            time_diff = (current_time - next_time).total_seconds()
                            if -60 <= time_diff <= -10:  # Next time is 10-60 seconds in the future
                                # Check task status again to avoid race condition
                                # Reload task from database to get current status
                                try:
                                    current_task = Task.get_task_by_id(task.id)
                                    if current_task.status != 'pending':
                                        logger.debug(f"Task {task.id} is no longer pending, skipping")
                                        continue
                                    
                                    # Prepare task data for queue
                                    task_data = {
                                        'task_id': task.id,
                                        'content': task.content,
                                        'cron_expression': task.cron_expression,
                                        'status': 'in_progress'
                                    }
                                    
                                    # Update task status to in_progress atomically
                                    # Using task.start() which updates status and sets started_at
                                    current_task.start()  # This updates status to 'in_progress' and sets started_at
                                    
                                    # Push to queue
                                    self.task_queue.put(task_data)
                                    tasks_added += 1
                                    task_added = True
                                    logger.info(f"Added periodic task {task.id} to queue: {task.content[:50]}... (cron: {task.cron_expression})")
                                except Exception as task_error:
                                    logger.error(f"Error processing task {task.id}: {task_error}")
                        else:
                            logger.warning(f"Invalid cron expression for task {task.id}: {task.cron_expression}")
                    except Exception as e:
                        logger.error(f"Error checking cron for task {task.id}: {e}")
                
                # Check tasks with scheduled_at (one-time scheduled tasks)
                # Only check if task hasn't been added yet from cron check
                if not task_added and task.scheduled_at:
                    try:
                        # Compare at minute level (ignore seconds and microseconds)
                        # Convert to string format "YYYY-MM-DD HH:MM" for comparison
                        # First convert scheduled_at to UTC to match current_time (which is UTC)
                        scheduled_at_utc = task.scheduled_at
                        if scheduled_at_utc.tzinfo is None:
                            # If scheduled_at is naive datetime, assume it's in UTC
                            scheduled_at_utc = scheduled_at_utc.replace(tzinfo=timezone.utc)
                        else:
                            # If scheduled_at has timezone info, convert to UTC
                            scheduled_at_utc = scheduled_at_utc.astimezone(timezone.utc)
                        
                        scheduled_minute_str = scheduled_at_utc.strftime("%Y-%m-%d %H:%M")
                        current_minute_str = current_time.strftime("%Y-%m-%d %H:%M")
                        
                        # Check if current datetime (at minute precision) matches scheduled datetime
                        # We only execute if current minute exactly matches scheduled minute
                        # This ensures task runs only once at the scheduled time
                        logger.debug(f"current_minute: {current_minute_str} scheduled_minute: {scheduled_minute_str}")
                        if current_minute_str == scheduled_minute_str:
                            # Check task status again to avoid race condition
                            try:
                                current_task = Task.get_task_by_id(task.id)
                                if current_task.status != 'pending':
                                    logger.debug(f"Task {task.id} is no longer pending, skipping")
                                    continue
                                
                                # Prepare task data for queue
                                task_data = {
                                    'task_id': task.id,
                                    'content': task.content,
                                    'scheduled_at': task.scheduled_at.isoformat(),
                                    'status': 'in_progress'
                                }
                                
                                # Update task status to in_progress atomically
                                current_task.start()  # This updates status to 'in_progress' and sets started_at
                                
                                # Push to queue
                                self.task_queue.put(task_data)
                                tasks_added += 1
                                logger.info(f"Added scheduled task {task.id} to queue: {task.content[:50]}... (scheduled at: {task.scheduled_at})")
                            except Exception as task_error:
                                logger.error(f"Error processing scheduled task {task.id}: {task_error}")
                    except Exception as e:
                        logger.error(f"Error checking scheduled_at for task {task.id}: {e}")
            
            if tasks_added > 0:
                logger.info(f"Added {tasks_added} tasks to queue for agent worker")
            else:
                logger.debug("No tasks to add to queue")
                
        except Exception as e:
            logger.error(f"Error in scan_task_for_agent_worker: {e}")

    def execute_task_from_queue(self) -> None:
        """
        Execute tasks from the queue using WorkerTeamAgent.
        This function is called every 60 seconds by the scheduler.
        
        It will:
        1. Get task from queue (non-blocking)
        2. Call WorkerTeamAgent to execute the task
        3. Update task status based on execution result
        
        For periodic tasks with cron expressions:
        - Reset status to 'pending' after execution (instead of 'done'/'failed')
        - Update scheduled_at to next execution time based on cron
        - Track execution history through execution_count and other fields
        
        For one-time scheduled tasks with scheduled_at:
        - Mark as done/failed after execution (not reset to pending)
        - No next scheduled time calculation
        """
        try:
            # Check if queue has tasks
            if self.task_queue.empty():
                logger.debug("Task queue is empty")
                return
            
            # Get task from queue (non-blocking with timeout)
            try:
                task_data = self.task_queue.get(timeout=1)
            except:
                logger.debug("No task available in queue")
                return
            
            task_id = task_data.get('task_id')
            content = task_data.get('content')
            cron_expression = task_data.get('cron_expression')
            scheduled_at_str = task_data.get('scheduled_at')
            
            logger.info(f"Executing task {task_id}: {content[:50]}...")
            
            # Check if WorkerTeamAgent is available
            if not self.worker_team_agent:
                logger.error("WorkerTeamAgent not initialized, cannot execute task")
                # Put task back in queue for retry
                self.task_queue.put(task_data)
                return
            
            try:
                # Import Task model for updating status
                from sonagent.persistence import Task
                from croniter import croniter
                
                # Get task from database
                task = Task.get_task_by_id(task_id)
                
                # Prepare input for worker agent
                user_input = f"Execute task with ID {task_id}: {content}"
                
                # Call worker team agent to process the task
                result = self.worker_team_agent.process_worker_request(
                    user_input=user_input,
                    conversation_id=f"task_{task_id}_{int(time.time())}",
                    user_id="system"
                )
                
                if result.get("success"):
                    # Task executed successfully
                    worker_response = result.get("worker_response", "Task executed")
                    
                    # Check if this is a periodic task with cron expression
                    if cron_expression and task.cron_expression:
                        # This is a periodic task - reset to pending for next execution
                        
                        # Calculate next execution time based on cron
                        next_scheduled_at = None
                        try:
                            base_time = task.scheduled_at or task.created_at or dt_now()
                            cron = croniter(cron_expression, base_time)
                            next_time = cron.get_next(datetime)
                            
                            # Make next_time timezone-aware (UTC)
                            if next_time.tzinfo is None:
                                next_time = next_time.replace(tzinfo=timezone.utc)
                            
                            next_scheduled_at = next_time
                            logger.info(f"Periodic task {task_id} scheduled for next execution at: {next_time}")
                        except Exception as cron_error:
                            logger.error(f"Error calculating next execution time for task {task_id}: {cron_error}")
                        
                        # Reset task for next execution
                        task.reset_for_next_periodic_execution(next_scheduled_at)
                        task.result = {"worker_response": worker_response, "execution_count": (task.execution_count or 0) + 1}
                        
                        # Update execution statistics
                        task.update_execution_data(
                            tokens_used=1000,  # Default estimate, should be updated with actual token usage
                            duration_seconds=None,
                            success=True
                        )
                        
                        logger.info(f"Periodic task {task_id} executed successfully and reset to pending for next run")
                        self.notify_status(f"Periodic task {task_id} completed and scheduled for next run: {content[:50]}...")
                    else:
                        # Regular one-time task (including scheduled_at tasks) - mark as done
                        task.complete(result={"worker_response": worker_response})
                        logger.info(f"Task {task_id} executed successfully")
                        self.notify_status(f"Task {task_id} completed: {content[:50]}...")
                        
                else:
                    # Task execution failed
                    error_msg = result.get("error", "Unknown error")
                    
                    # Check if this is a periodic task with cron expression
                    if cron_expression and task.cron_expression:
                        # Periodic task failed - reset to pending for retry (if retries left)
                        if task.retry_count < task.max_retries:
                            task.status = 'pending'
                            task.completed_at = dt_now()
                            task.result = {'error': error_msg, 'retry_count': task.retry_count}
                            
                            # Update execution statistics (failed)
                            task.update_execution_data(
                                tokens_used=1000,  # Default estimate
                                duration_seconds=None,
                                success=False
                            )
                            
                            Task.session.commit()
                            logger.warning(f"Periodic task {task_id} failed but reset to pending for retry (retry {task.retry_count}/{task.max_retries}): {error_msg}")
                            self.notify_status(f"Periodic task {task_id} failed but will retry: {error_msg[:100]}")
                        else:
                            # Max retries exceeded - mark as failed permanently
                            task.fail(error_message=f"Max retries exceeded: {error_msg}")
                            logger.error(f"Periodic task {task_id} failed permanently after {task.max_retries} retries: {error_msg}")
                            self.notify_status(f"Periodic task {task_id} failed permanently: {error_msg[:100]}")
                    else:
                        # Regular one-time task failed (including scheduled_at tasks)
                        task.fail(error_message=error_msg)
                        logger.error(f"Task {task_id} failed: {error_msg}")
                        self.notify_status(f"Task {task_id} failed: {error_msg}")
                    
            except Exception as e:
                logger.error(f"Error executing task {task_id}: {e}")
                
                # Update task status based on whether it's periodic or not
                try:
                    from sonagent.persistence import Task
                    task = Task.get_task_by_id(task_id)
                    
                    if task.cron_expression:
                        # Periodic task - check retry count
                        if task.retry_count < task.max_retries:
                            task.status = 'pending'
                            task.completed_at = dt_now()
                            task.result = {'error': str(e), 'retry_count': task.retry_count}
                            Task.session.commit()
                            logger.warning(f"Periodic task {task_id} execution error but reset to pending for retry: {str(e)[:100]}")
                        else:
                            task.fail(error_message=str(e))
                            logger.error(f"Periodic task {task_id} execution error after max retries: {str(e)[:100]}")
                    else:
                        # Regular task (including scheduled_at tasks)
                        task.fail(error_message=str(e))
                        logger.error(f"Task {task_id} execution error: {str(e)[:100]}")
                        
                except:
                    pass
                
                # Notify status
                self.notify_status(f"Task {task_id} execution error: {str(e)[:100]}")
            
            # Mark task as done in queue
            self.task_queue.task_done()
            
        except Exception as e:
            logger.error(f"Error in execute_task_from_queue: {e}")


    def scan_and_reload_skills(self) -> None:
        """
        Scan the skills directory for changes and reload skills if needed.
        This method is called every 10 seconds by the scheduler.
        """
        try:
            # Get current skill files in the directory
            skills_dir = Path(self.config['user_data_dir']).joinpath('skills')
            
            if not skills_dir.exists():
                logger.info(f"Skills directory does not exist, creating: {skills_dir}")
                try:
                    skills_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created skills directory: {skills_dir}")
                except Exception as e:
                    logger.error(f"Failed to create skills directory {skills_dir}: {e}")
                    return
                
            current_files = set()
            for entry in skills_dir.iterdir():
                if entry.suffix == '.py' and entry.is_file() and not entry.name.startswith('__'):
                    # Use file modification time and size to detect changes
                    stat = entry.stat()
                    file_key = f"{entry.name}:{stat.st_mtime}:{stat.st_size}"
                    current_files.add(file_key)
            
            # Check if files have changed since last scan
            if current_files != self.cached_skill_files:
                logger.info(f"Skill files changed. Current: {len(current_files)} files, Previous: {len(self.cached_skill_files)} files")
                self.cached_skill_files = current_files
                
                # Reload skills
                self.agent.reload_skills()
                logger.info("Skills reloaded due to directory changes")
            else:
                # Log only occasionally to avoid spam
                if time.time() - self.last_skill_scan_time > 60:  # Log once per minute
                    logger.debug(f"No changes in skill directory. Current skill count: {len(self.skills.skill_object_list)}")
                    self.last_skill_scan_time = time.time()
                    
        except Exception as e:
            logger.error(f"Error scanning skills directory: {e}")

    def scan_and_reload_tools(self) -> None:
        """
        Scan the tools directory for changes and reload tools if needed.
        This method is called every 30 seconds by the scheduler.
        Only scans and reloads, no status notifications.
        """
        try:
            if hasattr(self, 'tool_registry'):
                reloaded = self.tool_registry.scan_and_load_tools()
                if reloaded:
                    logger.info(f"Tools reloaded. Total tools: {len(self.tool_registry.tools)}")
                else:
                    # Log only occasionally to avoid spam
                    current_time = time.time()
                    if hasattr(self, 'last_tool_scan_time'):
                        if current_time - self.last_tool_scan_time > 300:  # Log once every 5 minutes
                            logger.debug(f"No changes in tools directory. Current tool count: {len(self.tool_registry.tools)}")
                            self.last_tool_scan_time = current_time
                    else:
                        self.last_tool_scan_time = current_time
            else:
                logger.warning("ToolRegistry not initialized, cannot scan tools")
                
        except Exception as e:
            logger.error(f"Error scanning tools directory: {e}")

    async def chat(self, input: str) -> str:
        """
        Process chat message using team agent.
        Main agent chỉ chịu trách nhiệm chat thông thường như một trợ lý.
        
        Args:
            input: User input message
            
        Returns:
            Assistant response
        """
        # Always use team agent if available
        if self.team_agent:
            try:
                result = await self.team_agent.process_user_request_async(
                    user_input=input,
                    conversation_id="default",
                    user_id="default"
                )
                print(result)
                print("===========================")
                
                if result.get("success"):
                    response = result.get("assistant_response", "No response generated")
                    
                    # Notify chat event
                    try:
                        self.notify_chat_event(response)
                    except Exception as e:
                        logger.error(f"Error notifying chat event: {e}")
                    
                    return response
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Team agent failed: {error_msg}")
                    return f"Error: {error_msg}"
                    
            except Exception as e:
                logger.error(f"Error in team agent chat: {e}")
                return f"Error processing your message: {str(e)}"
        else:
            # Fallback to original agent if team agent is not available
            logger.warning("Team agent not available, falling back to original agent")
            chat = await self.agent.chat(input)
            try:
                self.notify_chat_event(chat)
            except Exception as e:
                logger.error(f"Error notifying chat event: {e}")
            return chat
    
    async def remove_skill(self, skill_name: str) -> str:
        result = self.agent.remove_skill(skill_name)
        self.reload_skills()
        return result
    
    async def clear_short_term_memory(self) -> str:
        return await self.agent.clear_short_term_memory()

    async def show_task(self) -> str:
        return await self.agent.show_task()
    
    async def show_env(self) -> list:
        return await self.agent.show_env()
    
    async def remove_env(self, key: str) -> str:
        return await self.agent.remove_env(key)
    
    async def add_env(self, key: str, value: str, description: str) -> str:
        return await self.agent.add_env(key, value, description)
    
    def show_skills(self) -> str:
        return self.agent.show_skills()
    
    def reload_skills(self) -> str:
        return self.agent.reload_skills()
    
    # Tool management methods
    def show_tools(self) -> str:
        """
        Get formatted list of all loaded tools.
        
        Returns:
            Formatted tools list
        """
        if hasattr(self, 'tool_registry'):
            return self.tool_registry.format_tools_list()
        else:
            return "ToolRegistry not initialized"
    
    def reload_tools(self) -> str:
        """
        Force reload all tools.
        
        Returns:
            Reload status message
        """
        if hasattr(self, 'tool_registry'):
            self.tool_registry.reload_tools()
            return f"Tools reloaded. Total tools: {len(self.tool_registry.tools)}"
        else:
            return "ToolRegistry not initialized"
    
    async def execute_tool(self, tool_name: str, tool_args: str = "") -> str:
        """
        Execute a specific tool with arguments.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: JSON string of arguments
            
        Returns:
            Tool execution result
        """
        if not hasattr(self, 'tool_registry'):
            return "ToolRegistry not initialized"
        
        try:
            import json
            
            # Parse arguments if provided
            kwargs = {}
            if tool_args:
                try:
                    kwargs = json.loads(tool_args)
                    if not isinstance(kwargs, dict):
                        return f"Error: Arguments must be a JSON object (dict), got {type(kwargs)}"
                except json.JSONDecodeError as e:
                    return f"Error parsing JSON arguments: {str(e)}"
            
            # Check if tool exists
            if tool_name not in self.tool_registry.tool_functions:
                return f"Error: Tool '{tool_name}' not found. Available tools: {', '.join(self.tool_registry.tool_functions.keys())}"
            
            # Execute tool
            result = self.tool_registry.execute_tool(tool_name, **kwargs)
            return f"Tool '{tool_name}' executed successfully. Result:\n{result}"
            
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"
    
    # Team agent specific methods
    async def create_task_via_team(self, content: str, priority: int = 0) -> str:
        """
        Create a task using team agent.
        
        Args:
            content: Task description
            priority: Task priority
            
        Returns:
            Task creation result
        """
        if not self.team_agent:
            return "Team agent not initialized. Please switch to team mode first."
        
        try:
            # create_task_tool is decorated with @tool, so we need to call it properly
            result = self.team_agent.create_task_tool.entrypoint(
                content=content,
                priority=priority
            )
            
            if result.get("success"):
                task_id = result.get("task_id")
                return f"Task created successfully with ID: {task_id}"
            else:
                error_msg = result.get("error", "Unknown error")
                return f"Failed to create task: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error creating task via team: {e}")
            return f"Error creating task: {str(e)}"
    
    async def get_tasks_via_team(self, status: Optional[str] = None, limit: int = 10) -> str:
        """
        Get tasks using team agent.
        
        Args:
            status: Filter by task status
            limit: Maximum number of tasks
            
        Returns:
            Formatted task list
        """
        if not self.team_agent:
            return "Team agent not initialized. Please switch to team mode first."
        
        try:
            # get_tasks_tool is decorated with @tool, so we need to call it properly
            # The @tool decorator returns a Tool object with an entrypoint attribute
            tasks = self.team_agent.get_tasks_tool.entrypoint(
                status=status,
                limit=limit
            )
            
            if not tasks:
                return "📭 *No tasks found.*"
            
            if isinstance(tasks, list) and len(tasks) > 0 and "error" in tasks[0]:
                return f"❌ *Error retrieving tasks:* `{tasks[0].get('error')}`"
            
            # Define status emojis
            status_emojis = {
                'pending': '⏳',
                'in_progress': '⚙️',
                'done': '✅',
                'failed': '❌',
                'cancelled': '🚫'
            }
            
            # Filter tasks by status if specified
            if status:
                filtered_tasks = [t for t in tasks if t.get('status') == status]
                if not filtered_tasks:
                    return f"📭 *No tasks found with status:* `{status}`"
                tasks_to_display = filtered_tasks
            else:
                tasks_to_display = tasks
            
            # Prepare table data with only ID, Content, Status
            table_data = []
            for task in tasks_to_display:
                # Get status emoji
                emoji = status_emojis.get(task.get('status', 'pending'), '📝')
                
                # Format content (truncate)
                content = task.get('content', 'No content')
                content = content[:50] + ('...' if len(content) > 50 else '')
                
                # Add to table
                table_data.append([
                    f"{emoji} #{task.get('id', 'N/A')}",
                    content,
                    task.get('status', 'pending').replace('_', ' ').title()
                ])
            
            # Create table
            from tabulate import tabulate
            headers = ["ID", "Content", "Status"]
            table = tabulate(table_data, headers=headers, tablefmt="simple")
            
            # Add summary
            total_tasks = len(tasks)
            pending = len([t for t in tasks if t.get('status') == 'pending'])
            in_progress = len([t for t in tasks if t.get('status') == 'in_progress'])
            done = len([t for t in tasks if t.get('status') == 'done'])
            failed = len([t for t in tasks if t.get('status') == 'failed'])
            cancelled = len([t for t in tasks if t.get('status') == 'cancelled'])
            
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
                
        except Exception as e:
            logger.error(f"Error getting tasks via team: {e}")
            return f"❌ *Error retrieving tasks:* `{str(e)[:100]}`"
    
    async def update_task_via_team(self, task_id: int, status: str, 
                                  result_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Update a task using team agent.
        
        Args:
            task_id: Task ID
            status: New status
            result_data: Task result data
            
        Returns:
            Update result
        """
        if not self.team_agent:
            return "Team agent not initialized. Please switch to team mode first."
        
        try:
            # update_task_tool is decorated with @tool, so we need to call it properly
            update_result = self.team_agent.update_task_tool.entrypoint(
                task_id=task_id,
                status=status,
                result=result_data
            )
            
            if update_result.get("success"):
                return f"Task {task_id} updated successfully to status: {status}"
            else:
                error_msg = update_result.get("error", "Unknown error")
                return f"Failed to update task: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error updating task via team: {e}")
            return f"Error updating task: {str(e)}"
    
    async def get_chat_history_via_team(self, conversation_id: Optional[str] = None, 
                                       limit: int = 20) -> str:
        """
        Get chat history using team agent.
        
        Args:
            conversation_id: Conversation ID (uses current if None)
            limit: Maximum number of messages
            
        Returns:
            Formatted chat history
        """
        if not self.team_agent:
            return "Team agent not initialized. Please switch to team mode first."
        
        try:
            conv_id = conversation_id or self.conversation_id
            # get_chat_history_tool is decorated with @tool, so we need to call it properly
            messages = self.team_agent.get_chat_history_tool.entrypoint(
                conversation_id=conv_id,
                limit=limit
            )
            
            if not messages:
                return f"No chat history found for conversation: {conv_id}"
            
            if isinstance(messages, list) and len(messages) > 0 and "error" in messages[0]:
                return f"Error retrieving chat history: {messages[0].get('error')}"
            
            # Format messages for display
            history = []
            for i, msg in enumerate(messages, 1):
                role = msg.get('role', 'unknown').upper()
                content = msg.get('content', '')[:100]
                timestamp = msg.get('created_at', '')[:19]
                history.append(f"{i}. [{role}] {timestamp}: {content}...")
            
            return f"Chat History for {conv_id}:\n" + "\n".join(history)
                
        except Exception as e:
            logger.error(f"Error getting chat history via team: {e}")
            return f"Error retrieving chat history: {str(e)}"
 
    async def request_feedback_via_team(self, action: str, context: str) -> str:
        """
        Request human feedback using team agent.
        
        Args:
            action: The action requiring feedback
            context: Context about why feedback is needed
            
        Returns:
            Feedback request message
        """
        if not self.team_agent:
            return "Team agent not initialized. Please switch to team mode first."
        
        try:
            # request_feedback_tool is decorated with @tool, so we need to call it properly
            result = self.team_agent.request_feedback_tool.entrypoint(
                action=action,
                context=context
            )
            
            if result.get("success"):
                if result.get("needs_feedback"):
                    return f"Feedback requested for action: {action}\nContext: {context}\nPlease provide your feedback."
                else:
                    return f"Feedback processed for action: {action}"
            else:
                error_msg = result.get("error", "Unknown error")
                return f"Failed to request feedback: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error requesting feedback via team: {e}")
            return f"Error requesting feedback: {str(e)}"
    
    def get_team_agent_info(self) -> Dict[str, Any]:
        """
        Get information about the team agent.
        
        Returns:
            Team agent information dictionary
        """
        if not self.team_agent:
            return {"initialized": False, "message": "Team agent not initialized"}
        
        return {
            "initialized": True,
            "agent_type": "MainTeamAgent",
            "db_path": self.team_agent.db_path if hasattr(self.team_agent, 'db_path') else "unknown",
            "team_name": self.team_agent.team.name if hasattr(self.team_agent, 'team') else "unknown",
            "member_count": len(self.team_agent.team.members) if hasattr(self.team_agent, 'team') else 0,
            "conversation_id": self.conversation_id
        }
    
    def cleanup(self) -> None:
        """
        Cleanup pending resources on an already stopped bot
        :return: None
        """
        logger.info('Cleaning up modules ...')
        try:
            # Wrap db activities in shutdown to avoid problems if database is gone,
            # and raises further exceptions.
            logger.info('Cleaning up process ...')
        except Exception as e:
            logger.warning(f'Exception during cleanup: {e.__class__.__name__} {e}')

        # finally:
        #     self.strategy.ft_bot_cleanup()

        # RPC cleanup 
        # self.rpc.cleanup()
        # if self.emc:
        #     self.emc.shutdown()

    def startup(self) -> None:
        pass

    def process(self) -> None:
        # print("process")
        self._schedule.run_pending()

    def process_stopped(self) -> None:
        """
        handle process stopped
        """
        pass

    def notify_chat_event(self, msg: str, msg_type=RPCMessageType.CHAT) -> None:
        self.rpc.send_msg({
            'type': msg_type,
            'message': msg
        })


    def notify_status(self, msg: str, msg_type=RPCMessageType.STATUS) -> None:
        """
        Public method for users of this class (worker, etc.) to send notifications
        via RPC about changes in the bot status.
        """
        self.rpc.send_msg({
            'type': msg_type,
            'status': msg
        })
    
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
    
    def new_conversation(self) -> str:
        """
        Start a new conversation by generating a new conversation ID.
        
        Returns:
            New conversation ID
        """
        old_id = self.conversation_id
        self.conversation_id = self._generate_conversation_id()
        logger.info(f"Started new conversation: {old_id} -> {self.conversation_id}")
        return self.conversation_id
