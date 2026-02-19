"""
Worker Team implementation.
This team is responsible for:
1. Getting task lists and prioritizing them
2. Considering short-term and long-term goals (Targets)
3. Making trade-off decisions based on execution time and token usage
4. Tracking token usage per task execution
5. Coordinating with development team for implementation tasks
6. Updating task execution data when work is completed
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

from sonagent.constants import TOOL_CALL_LIMIT

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

# Import dev_team from the dev_team module
from sonagent.agents.dev_team import dev_team
from sonagent.agents.web_crawl_agent import web_crawl_agent
# Import new teams
from sonagent.agents.skills_and_tools_team import skills_and_tools_team
from sonagent.agents.research_team import research_team
from sonagent.agents.finance_team import finance_team
from sonagent.agents.general_task_team import general_task_team

logger = logging.getLogger(__name__)


class WorkerTeamAgent:
    """
    Worker team that prioritizes and executes tasks based on
    short-term and long-term goals, with token usage tracking.
    Includes development team as a member for implementation tasks.
    """
    
    def __init__(self, config: Dict[str, Any], db_path: str = "user_data/agno.db", memory_db_path: Optional[str] = None):
        """
        Initialize the worker team.
        
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
            description="Knowledge base for worker team tasks and targets",
            vector_db=ChromaDb(
                collection="worker_vectors", path=chroma_path, persistent_client=True,
                embedder=OpenAIEmbedder(id="text-embedding-3-small")
            ),
        )
        
        # Initialize the worker team
        self._init_worker_team()
        
        logger.info("WorkerTeam initialized")
    
    def _init_worker_team(self):
        """Initialize the worker team with specialized agents."""
        
        # Worker Agent - handles task prioritization and execution
        self.worker_agent = Agent(
            name="Worker Agent",
            role="Prioritize and execute tasks considering short-term and long-term goals",
            model=OpenAIResponses(id="gpt-4o-mini"),
            tools=[
                create_task_tool,
                get_task_list_tool,
                get_targets_tool,
                update_task_execution_data_tool,
                send_rpc_message_tool,
            ],
            tool_call_limit=TOOL_CALL_LIMIT,
            instructions="""
            You are a Worker Agent responsible for task prioritization and execution.
            
            Your responsibilities:
            1. Get task lists and analyze them
            2. Consider short-term and long-term goals (Targets)
            3. Prioritize tasks based on value scores (considering execution time, tokens, and goals)
            4. Execute tasks and track token usage
            5. Make trade-off decisions between short-term and long-term objectives
            6. Send notifications to users via RPC when tasks are completed or need attention
            7. If a task is too big, break it down and add the subtasks to the task list.
            8. Delegate development tasks to the Development Team
            9. Use update_task_execution_data_tool to update task status when work is completed
            10. if something relevent with github ->Delegate to dev tean 
            
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
            
            Use update_task_execution_data_tool to:
            - Update task status when work is completed
            - Record token usage and execution time
            - Mark tasks as successful or failed
            - Add notes or results to task execution
            
            When a task requires development work:
            - Delegate to the Development Team
            - Provide clear requirements and acceptance criteria
            - Monitor progress and provide feedback
            - Update task execution data when development is complete
            """,
            db=self.db,
            add_history_to_context=True,
            num_history_runs=10,
            knowledge=self.knowledge,
            search_knowledge=True,
            learning=LearningMachine(
                knowledge=self.knowledge,
                user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),     # Agent-driven, not automatic
                user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),       # Agent-driven, not automatic
                learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),  # Agent-driven
            ),
        )
        
        # Target Management Agent - handles target CRUD operations
        self.target_agent = Agent(
            name="Target Management Agent",
            role="Manage short-term and long-term goals (Targets)",
            model=OpenAIResponses(id="gpt-4o-mini"),
            tools=[
                get_targets_tool,
                add_target_tool,
                delete_target_tool,
                update_target_tool
            ],
            tool_call_limit=TOOL_CALL_LIMIT,
            instructions="""
            You are responsible for managing targets (goals) in the system.
            
            Your responsibilities:
            1. Get current targets and their status
            2. Add new targets based on user requests or strategic needs
            3. Update existing targets with progress or changes
            4. Delete completed or obsolete targets
            5. Ensure targets align with overall strategy
            
            Target types:
            - Short-term targets: Immediate objectives (days/weeks)
            - Long-term targets: Strategic goals (months/years)
            - Survival targets: Core operational objectives
            
            Always:
            - Validate target descriptions are clear and measurable
            - Check for duplicate or conflicting targets
            - Provide target IDs for reference
            - Confirm before deleting targets
            """,
            db=self.db,
            add_history_to_context=True,
            num_history_runs=5
        )
        
        # Initialize the worker team with all agents including dev_team
        self.worker_team = Team(
            name="Worker Team",
            model=OpenAIResponses(id="gpt-4o-mini"),
            tool_call_limit=TOOL_CALL_LIMIT,
            members=[
                self.worker_agent,
                self.target_agent,
                dev_team,  # Include the development team as a member
                skills_and_tools_team,  # Skills & Tools Team for creating new tools and skills
                research_team,  # Research Team for academic and general knowledge research
                finance_team,  # Finance Team for financial and market analysis
                web_crawl_agent,
                general_task_team,  # General Task Team for handling diverse tasks that don't fit specialized categories
            ],
            mode=TeamMode.coordinate,
            instructions="""
            You are the Worker Team responsible for task execution and goal management.
            
            Coordination Rules:
            1. For task execution, prioritization, and monitoring: delegate to Worker Agent
               - This includes: executing tasks, tracking progress, sending notifications
               - Examples: "execute task X", "prioritize tasks", "check task status", "send update"
               - Worker Agent will use update_task_execution_data_tool to update task status when completed
            
            2. For target/goal management: delegate to Target Management Agent
               - This includes: adding, updating, deleting targets
               - Examples: "add new target", "update target progress", "show current targets"
            
            3. For development and implementation tasks: delegate to Development Team
               - This includes: coding, system design, infrastructure, deployment
               - Examples: "implement feature X", "fix bug Y", "deploy to production"
               - Development Team will coordinate with Product Owner, Backend Dev, and DevOps
            
            4. For creating new tools or skills: delegate to Skills & Tools Team
               - This includes: creating new Python tools, creating Agno skills
               - Examples: "create a tool for data processing", "create a skill for code review"
               - Skills & Tools Team will create files in user_data/tools/ and user_data/skills/
            
            5. For research and knowledge gathering: delegate to Research Team
               - This includes: academic papers, general knowledge, tech community trends
               - Examples: "research AI agents", "find information about quantum computing"
               - Research Team includes Arxiv Researcher and Wikipedia Researcher
            
            6. For financial and market analysis: delegate to Finance Team
               - This includes: stock prices, company fundamentals, market trends, tech community sentiment
               - Examples: "analyze NVIDIA stock", "check tech trends on Hacker News"
               - Finance Team includes Finance Analyst and HackerNews Analyst
            
            7. For tasks that don't fit into specialized categories: delegate to General Task Team
               - This includes: diverse problems, multi-domain tasks, experimental work, system administration
               - Examples: "help me with a complex multi-step problem", "automate this workflow", "troubleshoot this issue"
               - General Task Team has dynamic tools and can handle anything that doesn't clearly belong elsewhere
            
            8. For complex tasks that span multiple areas: coordinate between agents
            
            9. for get, read or crawl web conntent form a website rout to eb Crawl Agent

            Key principles:
            - Always track token usage for tasks
            - Consider both short-term and long-term goals
            - Make trade-off decisions based on value scores
            - Break down large tasks into manageable subtasks
            - Notify users when tasks are completed or need attention
            - Delegate appropriately based on task type
            - Update task execution data when work is completed
            
            Development workflow:
            1. When a task requires development work, delegate to Development Team
            2. Development Team will coordinate with Product Owner for requirements
            3. Development Team will implement with Backend Dev and DevOps
            4. Monitor progress and provide feedback as needed
            5. Notify users when development tasks are completed
            6. Update task execution data with results
            
            Tool/Skill creation workflow:
            1. When user requests new functionality, delegate to Skills & Tools Team
            2. Skills & Tools Team will create appropriate Python tools or Agno skills
            3. New tools go to user_data/tools/, skills go to user_data/skills/
            4. Test new tools/skills when possible
            5. Notify user when creation is complete
            
            Research workflow:
            1. When research is needed, delegate to Research Team
            2. Research Team will gather information from academic and general knowledge sources
            3. Present findings in structured format
            4. Include citations and sources
            
            Finance workflow:
            1. When financial/market analysis is needed, delegate to Finance Team
            2. Finance Team will gather stock data and tech community sentiment
            3. Combine quantitative and qualitative analysis
            4. Present insights with clear tables and summaries
            
            Always maintain:
            - Task execution history (using update_task_execution_data_tool)
            - Target alignment
            - Resource optimization
            - User communication
            """,
            db=self.db,
            enable_agentic_memory=True,
            add_history_to_context=True,
            num_history_runs=10,
            show_members_responses=True,
            search_knowledge=True,
            knowledge=self.knowledge,
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
        Process a worker request through the worker team.
        
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
            
            # Process request through worker team
            worker_response = self.worker_team.run(user_input, user_id=user_id, session_id=conversation_id)
            
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
        Process a worker request asynchronously through the worker team.
        
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
            
            # Process request through worker team asynchronously
            worker_response = await self.worker_team.arun(user_input, user_id=user_id, session_id=conversation_id)
            
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
        Get information about the worker team.
        
        Returns:
            Worker team information dictionary
        """
        return {
            "initialized": True,
            "agent_type": "WorkerTeamAgent",
            "db_path": self.db_path,
            "team_name": self.worker_team.name if hasattr(self, 'worker_team') else "unknown",
            "team_members": len(self.worker_team.members) if hasattr(self, 'worker_team') and hasattr(self.worker_team, 'members') else 0,
            "worker_agent_name": self.worker_agent.name if hasattr(self, 'worker_agent') else "unknown",
            "target_agent_name": self.target_agent.name if hasattr(self, 'target_agent') else "unknown",
            "dev_team_included": True,
            "skills_and_tools_team_included": True,
            "research_team_included": True,
            "finance_team_included": True,
            "general_task_team_included": True,
            "knowledge_base": self.knowledge.name if hasattr(self, 'knowledge') else "unknown"
        }