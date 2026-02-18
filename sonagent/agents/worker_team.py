"""
Worker Team Agent implementation.
This agent is responsible for:
1. Getting task lists and prioritizing them
2. Considering short-term and long-term goals (Targets)
3. Making trade-off decisions based on execution time and token usage
4. Tracking token usage per task execution
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
import time

from agno.agent import Agent
from agno.team import Team, TeamMode
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.knowledge import Knowledge
from agno.vectordb.chroma import ChromaDb
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.learn import (
    LearningMachine,
    LearningMode,
    UserProfileConfig,
    UserMemoryConfig,
    LearnedKnowledgeConfig,
)

from sonagent.persistence import Task, Target
from sonagent.utils.datetime_helpers import dt_now
from sonagent.agents.worker_agent_tools import (
    get_task_list_tool,
    get_targets_tool,
    update_task_execution_data_tool,
    add_target_tool,
    delete_target_tool,
    update_target_tool,
    send_rpc_message_tool
)

from sonagent.agents.agent_tools import (
    create_task_tool
)

logger = logging.getLogger(__name__)


class WorkerTeamAgent:
    """
    Worker team agent that prioritizes and executes tasks based on
    short-term and long-term goals, with token usage tracking.
    """
    
    def __init__(self, config: Dict[str, Any], db_path: str = "user_data/agno.db", memory_db_path: Optional[str] = None):
        """
        Initialize the worker team agent.
        
        Args:
            config: Configuration dictionary
            db_path: Path to SQLite database file
            memory_db_path: Path for memory database (ChromaDB). If None, uses default "tmp/chromadb"
        """
        self.config = config
        self.db_path = db_path
        
        # Initialize Agno SQLite database
        self.db = SqliteDb(db_file=db_path)
        
        # Initialize knowledge base with ChromaDB
        chroma_path = memory_db_path if memory_db_path else "tmp/chromadb"
        self.knowledge = Knowledge(
            name="Worker Knowledge Base",
            description="Knowledge base for worker agent tasks and targets",
            vector_db=ChromaDb(
                collection="worker_vectors", path=chroma_path, persistent_client=True,
                embedder=OpenAIEmbedder(id="text-embedding-3-small")
            ),
        )
        
        # Initialize the worker agent
        self._init_worker_agent()
        
        logger.info("WorkerTeamAgent initialized")
    
    def _init_worker_agent(self):
        """Initialize the worker agent with tools."""
        
        self.worker_agent = Agent(
            name="Worker Agent",
            role="Prioritize and execute tasks considering short-term and long-term goals",
            model=OpenAIResponses(id="gpt-4o-mini"),
            tools=[
                create_task_tool,
                get_task_list_tool,
                get_targets_tool,
                update_task_execution_data_tool,
                add_target_tool,
                delete_target_tool,
                update_target_tool,
                send_rpc_message_tool,
            ],
            instructions="""
            You are a Worker Agent responsible for task prioritization and execution.
            
            Your responsibilities:
            1. Get task lists and analyze them
            2. Consider short-term and long-term goals (Targets)
            3. Prioritize tasks based on value scores (considering execution time, tokens, and goals)
            4. Execute tasks and track token usage
            5. Make trade-off decisions between short-term and long-term objectives
            6. Send notifications to users via RPC when tasks are completed or need attention
            
            Key concepts:
            - Short-term goals: Immediate tasks with quick returns
            - Long-term goals: Strategic objectives with future benefits
            - Token usage: Measure of computational cost for each task
            - Value score: Combined metric of priority, estimated tokens, and alignment with goals
            - RPC notifications: Send status updates to users via Telegram, API, etc.
            
            Always consider:
            - Task execution history (tokens used, success rate)
            - Target urgency and progress
            - Resource constraints (token budgets)
            - Time-value tradeoffs
            - Notify users when tasks are completed or need human intervention
            
            Use send_rpc_message_tool to:
            - Notify users when tasks are completed
            - Alert users when tasks need attention or approval
            - Send status updates on long-running tasks
            - Report errors or issues that require human intervention
            """,
            db=self.db,
            add_history_to_context=True,
            num_history_runs=5,
            knowledge=self.knowledge,
            search_knowledge=True,
            learning=LearningMachine(
                knowledge=self.knowledge,
                user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),     # Agent-driven, not automatic
                user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),       # Agent-driven, not automatic
                learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),  # Agent-driven
            ),
        )
    
    def process_worker_request(self, user_input: str, conversation_id: str = None, 
                              user_id: str = "default") -> Dict[str, Any]:
        """
        Process a worker request through the worker agent.
        
        Args:
            user_input: User's message or task request
            conversation_id: Conversation identifier (generated if None)
            user_id: User identifier
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = f"worker_conv_{int(dt_now().timestamp())}_{user_id}"
            
            # Process request through worker agent
            worker_response = self.worker_agent.run(user_input, user_id=user_id, session_id=conversation_id)
            
            # Create result
            result = {
                "success": True,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_input": user_input,
                "worker_response": worker_response.content,
                "message": "Worker request processed successfully"
            }
            
            logger.info(f"Worker request processed: conversation={conversation_id}, user={user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing worker request: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process worker request"
            }
    
    async def process_worker_request_async(self, user_input: str, conversation_id: str = None,
                                          user_id: str = "default") -> Dict[str, Any]:
        """
        Process a worker request asynchronously through the worker agent.
        
        Args:
            user_input: User's message or task request
            conversation_id: Conversation identifier (generated if None)
            user_id: User identifier
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = f"worker_conv_{int(dt_now().timestamp())}_{user_id}"
            
            # Process request through worker agent asynchronously
            worker_response = await self.worker_agent.arun(user_input, user_id=user_id, session_id=conversation_id)
            
            # Check if the run is paused and needs confirmation
            if hasattr(worker_response, 'is_paused') and worker_response.is_paused:
                logger.info(f"Worker run paused. Active requirements: {len(worker_response.active_requirements) if hasattr(worker_response, 'active_requirements') else 'unknown'}")
                
                # Handle paused run - return special result indicating need for confirmation
                result = {
                    "success": True,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "user_input": user_input,
                    "worker_response": None,
                    "run_paused": True,
                    "run_id": worker_response.run_id if hasattr(worker_response, 'run_id') else None,
                    "active_requirements": self._extract_requirements_info(worker_response),
                    "message": "Worker run paused for confirmation. Please confirm or reject the action."
                }
                
                logger.info(f"Async worker request paused: conversation={conversation_id}, user={user_id}")
                return result
            
            # Create result
            result = {
                "success": True,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_input": user_input,
                "worker_response": worker_response.content,
                "message": "Worker request processed successfully"
            }
            
            logger.info(f"Async worker request processed: conversation={conversation_id}, user={user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing async worker request: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process worker request"
            }
    
    def _extract_requirements_info(self, run_response) -> List[Dict[str, Any]]:
        """
        Extract information about active requirements from a paused run response.
        
        Args:
            run_response: The paused run response
            
        Returns:
            List of requirement information dictionaries
        """
        requirements_info = []
        
        if hasattr(run_response, 'active_requirements'):
            for requirement in run_response.active_requirements:
                req_info = {
                    "type": "unknown",
                    "tool_name": None,
                    "tool_args": None,
                    "needs_confirmation": False,
                    "needs_user_input": False,
                    "is_external_tool_execution": False
                }
                
                if hasattr(requirement, 'needs_confirmation') and requirement.needs_confirmation:
                    req_info["type"] = "confirmation"
                    req_info["needs_confirmation"] = True
                    if hasattr(requirement, 'tool'):
                        req_info["tool_name"] = getattr(requirement.tool, 'tool_name', None)
                        req_info["tool_args"] = getattr(requirement.tool, 'tool_args', None)
                
                elif hasattr(requirement, 'needs_user_input') and requirement.needs_user_input:
                    req_info["type"] = "user_input"
                    req_info["needs_user_input"] = True
                    if hasattr(requirement, 'user_input_schema'):
                        req_info["user_input_schema"] = requirement.user_input_schema
                
                elif hasattr(requirement, 'is_external_tool_execution') and requirement.is_external_tool_execution:
                    req_info["type"] = "external_execution"
                    req_info["is_external_tool_execution"] = True
                    if hasattr(requirement, 'tool_execution'):
                        req_info["tool_name"] = getattr(requirement.tool_execution, 'tool_name', None)
                        req_info["tool_args"] = getattr(requirement.tool_execution, 'tool_args', None)
                
                requirements_info.append(req_info)
        
        return requirements_info
    
    def get_worker_agent_info(self) -> Dict[str, Any]:
        """
        Get information about the worker agent.
        
        Returns:
            Worker agent information dictionary
        """
        return {
            "initialized": True,
            "agent_type": "WorkerTeamAgent",
            "db_path": self.db_path,
            "agent_name": self.worker_agent.name if hasattr(self, 'worker_agent') else "unknown",
            "tools_count": len(self.worker_agent.tools) if hasattr(self, 'worker_agent') and hasattr(self.worker_agent, 'tools') else 0,
            "knowledge_base": self.knowledge.name if hasattr(self, 'knowledge') else "unknown"
        }