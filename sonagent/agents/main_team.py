"""
Main Team Agent implementation using Agno framework.
This team agent coordinates multiple specialized agents to handle user requests
via RPC, with human feedback integration and persistent chat history.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from agno.agent import Agent
from agno.team import Team, TeamMode
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIResponses
from agno.tools import tool
from agno.tools.function import UserInputField
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

from sonagent.persistence import Task, ChatMessage, Conversation
from sonagent.utils.datetime_helpers import dt_now
from sonagent.agents.agent_tools import (
    create_task_tool,
    get_tasks_tool,
    update_task_tool,
    delete_task_tool,
    save_chat_message_tool,
    get_chat_history_tool,
    extract_tom_tool,
    analyze_intent_tool,
    request_feedback_tool,
    process_feedback_tool,
    coordinate_agents_tool,
    respond_to_user_tool
)

logger = logging.getLogger(__name__)


class MainTeamAgent:
    """
    Main team agent that coordinates specialized agents for handling user requests.
    Integrates with RPC, handles human feedback, and maintains persistent chat history.
    """
    
    def __init__(self, config: Dict[str, Any], db_path: str = "user_data/agno.db", memory_db_path: Optional[str] = None):
        """
        Initialize the main team agent.
        
        Args:
            config: Configuration dictionary
            db_path: Path to SQLite database file
            memory_db_path: Path for memory database (ChromaDB). If None, uses default "tmp/chromadb"
        """
        self.config = config
        self.db_path = db_path
        
        # Initialize Agno SQLite database
        self.db = SqliteDb(db_file=db_path)
        
        # Store for paused runs
        self.paused_runs: Dict[str, Any] = {}
        chroma_path = memory_db_path if memory_db_path else "tmp/chromadb"
        # Use provided memory_db_path or default


        self.knowledge = Knowledge(
            name="Knowledge Base",
            description="user knowledge",
            vector_db=ChromaDb(
                collection="vectors", path=chroma_path, persistent_client=True,
                embedder=OpenAIEmbedder(id="text-embedding-3-small")
            ),
        )
        
        # Initialize specialized agents
        self._init_agents()
        
        # Initialize the main team
        self._init_team()
        
        logger.info("MainTeamAgent initialized")
    
    def _init_agents(self):
        """Initialize specialized agents for the team."""
        
        # Debug: Check what type of objects our tools are
        logger.debug(f"Initializing agents with tools...")
        
        # Use the imported tool functions from agent_tools.py
        # These are regular functions, not instance methods
        
        # Task Management Agent - handles task creation and management
        self.task_agent = Agent(
            name="Task Agent",
            role="Create, manage, and track tasks in the system",
            model=OpenAIResponses(id="gpt-4o-mini"),
            tools=[
                create_task_tool,
                get_tasks_tool,
                update_task_tool,
                delete_task_tool
            ],
            instructions="""
            You are responsible for task management. When users request tasks, create a task with the information provided.
            
            Key principles:
            1. The most important field is 'content' (task description) - this is REQUIRED
            2. 'cron_expression' and 'scheduled_at' are OPTIONAL - if the user doesn't provide them, leave them empty
            3. If the user provides incomplete information (e.g., only content), still create the task with empty optional fields
            4. Priority defaults to 0 (low) if not specified
            5. Always provide task IDs for reference
            6. After creating a task, ALWAYS inform the user that the task has been saved to the database
            7. Provide clear confirmation messages in Vietnamese when appropriate
            
            When creating a task:
            - Extract the task content from the user's request
            - Determine priority if mentioned (high=2, medium=1, low=0)
            - If the user specifies a schedule (e.g., "every day at 9 AM"), convert to cron_expression
            - If the user specifies a specific date/time (e.g., "tomorrow at 10:00"), convert to scheduled_at datetime object
            - If schedule information is missing, leave cron_expression and scheduled_at empty
            
            When a task is created successfully, make sure to tell the user:
            - The task has been created and saved to the database
            - The task ID for reference
            - The task details (content, priority, status)
            - Any schedule information (cron_expression or scheduled_at) if provided
            """,
            db=self.db,
            add_history_to_context=True,
            num_history_runs=3
        )
        
        # Theory of Mind (TOM) Agent - extracts user's mental state, beliefs, and intentions
        self.tom_agent = Agent(
            name="TOM Agent",
            role="Extract and analyze user's Theory of Mind (beliefs, intentions, mental state)",
            model=OpenAIResponses(id="gpt-4o-mini"),
            tools=[
                extract_tom_tool,
                analyze_intent_tool
            ],
            instructions="""
            You analyze user's Theory of Mind (TOM). Your responsibilities:
            1. Extract user's beliefs, desires, intentions, and mental state from conversations
            2. Analyze user intent and predict future actions
            3. Maintain a model of user's knowledge and perspective
            4. Detect changes in user's emotional state or preferences
            
            Focus on understanding:
            - What does the user know/believe?
            - What does the user want/desire?
            - What are the user's intentions?
            - How does the user feel about topics?
            - What are the user's preferences and values?
            """,
            db=self.db,
            add_history_to_context=True,
            num_history_runs=3,
            knowledge=self.knowledge,
            search_knowledge=True,
            learning=LearningMachine(
                knowledge=self.knowledge,
                user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),     # Agent-driven, not automatic
                user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),       # Agent-driven, not automatic
                learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),  # Agent-driven
            ),
        )
        
        # Human Feedback Agent - handles user feedback and approvals
        self.feedback_agent = Agent(
            name="Feedback Agent",
            role="Collect and process human feedback for agent actions",
            model=OpenAIResponses(id="gpt-4o-mini"),
            tools=[
                request_feedback_tool,
                process_feedback_tool
            ],
            instructions="""
            You handle human feedback and approvals. Your responsibilities:
            1. Request user feedback when agent actions need approval
            2. Process and incorporate user feedback into agent decisions
            3. Handle confirmation requests for sensitive operations
            4. Maintain a record of user feedback for learning
            """,
            db=self.db,
            add_history_to_context=True,
            num_history_runs=3
        )
        
        # General Assistant Agent - handles general queries and coordination
        self.assistant_agent = Agent(
            name="Assistant Agent",
            role="Handle general user queries and coordinate with other agents",
            model=OpenAIResponses(id="gpt-4o-mini"),
            tools=[
                coordinate_agents_tool,
                respond_to_user_tool,
                save_chat_message_tool,
                get_chat_history_tool
            ],
            instructions="""
            You are the primary interface for users. Your responsibilities:
            1. Handle general user queries and conversations
            2. Coordinate with specialized agents when needed
            3. Provide clear and helpful responses
            4. Route requests to appropriate agents
            5. Save chat messages to persistent storage
            6. Retrieve conversation history when needed
            
            Always maintain conversation context and ensure chat history consistency.
            """,
            db=self.db,
            add_history_to_context=True,
            num_history_runs=3,
            
            search_knowledge=True,
            learning=LearningMachine(
                knowledge=self.knowledge,
                user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),     # Agent-driven, not automatic
                user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),       # Agent-driven, not automatic
                learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),  # Agent-driven
            ),

        )
        
        logger.debug(f"Agents initialized successfully")
    
    def _init_team(self):
        """Initialize the main team with all agents."""
        self.team = Team(
            name="Main Team",
            model=OpenAIResponses(id="gpt-4o-mini"),
            members=[
                self.assistant_agent,
                self.task_agent,
                self.tom_agent,
                self.feedback_agent
            ],
            mode=TeamMode.coordinate,
            instructions=f"""
            You are the main team coordinating multiple specialized agents.
            
            Coordination Rules:
            1. For task-related requests (create, update, check tasks): delegate to Task Agent
            2. For understanding user's mental state, beliefs, intentions: delegate to TOM Agent
            3. When user feedback or approval is needed: delegate to Feedback Agent
            4. For general queries and coordination: handle with Assistant Agent or delegate appropriately
            
            Always:
            - Save important conversations to chat history
            - Extract and update user's Theory of Mind when relevant
            - Maintain conversation context across sessions
            - If create task done tell user for end 

            Timenow: {datetime.now()}
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
    

    def _save_chat_message(self, conversation_id: str, role: str, 
                          content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Internal method to save a chat message to persistent storage.
        
        Args:
            conversation_id: Unique conversation identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional metadata
            
        Returns:
            Dictionary with save information
        """
        try:
            message = ChatMessage.create_message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                metadata=metadata
            )
            
            # Also update conversation metadata
            Conversation.create_or_update(
                conversation_id=conversation_id,
                title=metadata.get("title") if metadata else None,
                metadata=metadata
            )
            
            logger.debug(f"Chat message saved: Conversation={conversation_id}, Role={role}")
            
            return {
                "success": True,
                "message_id": message.id,
                "conversation_id": message.conversation_id,
                "role": message.role,
                "created_at": message.created_at.isoformat() if message.created_at else None,
                "message": "Chat message saved successfully"
            }
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save chat message"
            }
    

    def _extract_tom(self, conversation_text: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Internal method to extract Theory of Mind (TOM) from conversation text.
        
        Args:
            conversation_text: The conversation text to analyze
            user_id: ID of the user
            
        Returns:
            Dictionary with TOM analysis
        """
        try:
            # This would typically use an LLM to analyze the conversation
            # For now, we'll create a structured analysis
            
            tom_analysis = {
                "user_id": user_id,
                "timestamp": dt_now().isoformat(),
                "extracted_beliefs": [],
                "inferred_intentions": [],
                "emotional_state": "neutral",
                "knowledge_level": "medium",
                "preferences": [],
                "uncertainties": [],
                "summary": ""
            }
            
            # Simple keyword-based analysis (in production, use LLM)
            text_lower = conversation_text.lower()
            
            # Extract potential beliefs
            belief_keywords = ["think", "believe", "know", "feel", "opinion"]
            for keyword in belief_keywords:
                if keyword in text_lower:
                    tom_analysis["extracted_beliefs"].append(f"User expresses {keyword} about topic")
            
            # Extract intentions
            intent_keywords = ["want", "need", "would like", "plan to", "going to"]
            for keyword in intent_keywords:
                if keyword in text_lower:
                    tom_analysis["inferred_intentions"].append(f"User indicates {keyword}")
            
            # Emotional analysis
            positive_words = ["happy", "good", "great", "excited", "love"]
            negative_words = ["sad", "bad", "angry", "frustrated", "hate"]
            
            if any(word in text_lower for word in positive_words):
                tom_analysis["emotional_state"] = "positive"
            elif any(word in text_lower for word in negative_words):
                tom_analysis["emotional_state"] = "negative"
            
            # Create summary
            tom_analysis["summary"] = (
                f"Extracted {len(tom_analysis['extracted_beliefs'])} beliefs and "
                f"{len(tom_analysis['inferred_intentions'])} intentions. "
                f"Emotional state: {tom_analysis['emotional_state']}"
            )
            
            logger.info(f"TOM analysis extracted: {tom_analysis['summary']}")
            
            return {
                "success": True,
                "tom_analysis": tom_analysis,
                "message": "TOM analysis completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error extracting TOM: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to extract TOM"
            }
    

    def _determine_agent_types(self, request: str) -> List[str]:
        """
        Determine which agent types should handle a request.
        
        Args:
            request: User request text
            
        Returns:
            List of agent type names
        """
        request_lower = request.lower()
        agent_types = ["assistant"]  # Always include assistant
        
        # Check for task-related keywords
        task_keywords = ["task", "todo", "create", "update", "check", "status", "priority"]
        if any(keyword in request_lower for keyword in task_keywords):
            agent_types.append("task")
        
        # Check for TOM-related keywords
        tom_keywords = ["think", "believe", "feel", "want", "need", "intend", "opinion"]
        if any(keyword in request_lower for keyword in tom_keywords):
            agent_types.append("tom")
        
        # Check for feedback-related keywords
        feedback_keywords = ["feedback", "approve", "confirm", "reject", "like", "dislike"]
        if any(keyword in request_lower for keyword in feedback_keywords):
            agent_types.append("feedback")
        
        return list(set(agent_types))  # Remove duplicates
    
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
    
 
    def process_user_request(self, user_input: str, conversation_id: str = None, 
                            user_id: str = "default") -> Dict[str, Any]:
        """
        Process a user request through the team agent.
        
        Args:
            user_input: User's message
            conversation_id: Conversation identifier (generated if None)
            user_id: User identifier
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = f"conv_{int(datetime.now().timestamp())}_{user_id}"
            
            # Save user message to chat history
            self._save_chat_message(
                conversation_id=conversation_id,
                role="user",
                content=user_input,
                metadata={"user_id": user_id}
            )
            
            # Extract TOM from user input
            tom_result = self._extract_tom(user_input, user_id)
            
            # Process request through team
            team_response = self.team.run(user_input, user_id=user_id, session_id=conversation_id)
            
            # Save assistant response to chat history
            if team_response.content:
                self._save_chat_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=team_response.content,
                    metadata={"agent": "main_team"}
                )
            
            # Create result
            result = {
                "success": True,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_input": user_input,
                "assistant_response": team_response.content,
                "tom_analysis": tom_result.get("tom_analysis") if tom_result.get("success") else None,
                "message": "Request processed successfully"
            }
            
            logger.info(f"Request processed: conversation={conversation_id}, user={user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing user request: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process user request"
            }
    
    async def process_user_request_async(self, user_input: str, conversation_id: str = None,
                                        user_id: str = "default") -> Dict[str, Any]:
        """
        Process a user request asynchronously through the team agent.
        
        Args:
            user_input: User's message
            conversation_id: Conversation identifier (generated if None)
            user_id: User identifier
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = f"conv_{int(datetime.now().timestamp())}_{user_id}"
            
            # Save user message to chat history
            self._save_chat_message(
                conversation_id=conversation_id,
                role="user",
                content=user_input,
                metadata={"user_id": user_id}
            )
            
            # Extract TOM from user input
            tom_result = self._extract_tom(user_input, user_id)
            
            # Debug: Log before calling team.arun
            logger.debug(f"Calling team.arun with input: {user_input}")
            
            # Process request through team asynchronously
            team_response = await self.team.arun(user_input, user_id=user_id, session_id=conversation_id)
            
            # Check if the run is paused and needs confirmation
            if hasattr(team_response, 'is_paused') and team_response.is_paused:
                logger.info(f"Team run paused. Active requirements: {len(team_response.active_requirements) if hasattr(team_response, 'active_requirements') else 'unknown'}")
                
                # Handle paused run - return special result indicating need for confirmation
                result = {
                    "success": True,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "user_input": user_input,
                    "assistant_response": None,
                    "tom_analysis": tom_result.get("tom_analysis") if tom_result.get("success") else None,
                    "run_paused": True,
                    "run_id": team_response.run_id if hasattr(team_response, 'run_id') else None,
                    "active_requirements": self._extract_requirements_info(team_response),
                    "message": "Team run paused for confirmation. Please confirm or reject the action."
                }
                
                logger.info(f"Async request paused: conversation={conversation_id}, user={user_id}")
                return result
            
            # Save assistant response to chat history
            if team_response.content:
                self._save_chat_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=team_response.content,
                    metadata={"agent": "main_team"}
                )
            
            # Create result
            result = {
                "success": True,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_input": user_input,
                "assistant_response": team_response.content,
                "tom_analysis": tom_result.get("tom_analysis") if tom_result.get("success") else None,
                "message": "Request processed successfully"
            }
            
            logger.info(f"Async request processed: conversation={conversation_id}, user={user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing async user request: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process user request"
            }
    
    async def handle_confirmation(self, run_id: str, confirm: bool, 
                                 confirmation_note: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle confirmation for a paused team run.
        
        Args:
            run_id: The run ID to continue
            confirm: Whether to confirm (True) or reject (False) the action
            confirmation_note: Optional note to provide when rejecting
            
        Returns:
            Dictionary with continuation results
        """
        try:
            logger.info(f"Handling confirmation for run {run_id}: confirm={confirm}, note={confirmation_note}")
            
            # In Agno, when a run is paused, we need to:
            # 1. Get the run response (which should be stored somewhere)
            # 2. Handle the active requirements
            # 3. Continue the run
            
            # For now, we'll implement a simplified version
            # In production, you would need to store run responses and retrieve them by run_id
            
            # Since we can't easily retrieve the run by ID, we'll create a new approach
            # The system should handle this at the RPC level by storing the paused run
            
            return {
                "success": False,
                "error": "Run retrieval not implemented",
                "message": "Please implement run storage and retrieval for paused runs"
            }
            
        except Exception as e:
            logger.error(f"Error handling confirmation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to handle confirmation"
            }
    
    async def continue_paused_run(self, run_response, confirm: bool = True,
                                 confirmation_note: Optional[str] = None) -> Dict[str, Any]:
        """
        Continue a paused run after handling confirmation.
        
        Args:
            run_response: The paused run response
            confirm: Whether to confirm (True) or reject (False) the action
            confirmation_note: Optional note to provide when rejecting
            
        Returns:
            Dictionary with continuation results
        """
        try:
            if not hasattr(run_response, 'is_paused') or not run_response.is_paused:
                return {
                    "success": False,
                    "error": "Run is not paused",
                    "message": "Cannot continue a run that is not paused"
                }
            
            # Handle active requirements
            if hasattr(run_response, 'active_requirements'):
                for requirement in run_response.active_requirements:
                    if hasattr(requirement, 'needs_confirmation') and requirement.needs_confirmation:
                        if confirm:
                            # Confirm the requirement
                            if hasattr(requirement, 'confirm'):
                                requirement.confirm()
                            elif hasattr(requirement, 'confirmed'):
                                requirement.confirmed = True
                        else:
                            # Reject the requirement
                            if hasattr(requirement, 'reject'):
                                requirement.reject()
                            elif hasattr(requirement, 'confirmed'):
                                requirement.confirmed = False
                            
                            # Add confirmation note if provided
                            if confirmation_note and hasattr(requirement, 'confirmation_note'):
                                requirement.confirmation_note = confirmation_note
            
            # Continue the run
            continued_response = await self.team.acontinue_run(run_response=run_response)
            
            # Check if the continued run is also paused (might need more input)
            if hasattr(continued_response, 'is_paused') and continued_response.is_paused:
                return {
                    "success": True,
                    "run_paused_again": True,
                    "run_id": continued_response.run_id if hasattr(continued_response, 'run_id') else None,
                    "active_requirements": self._extract_requirements_info(continued_response),
                    "message": "Run continued but paused again for additional requirements"
                }
            
            # Run completed successfully
            return {
                "success": True,
                "assistant_response": continued_response.content if hasattr(continued_response, 'content') else None,
                "run_id": continued_response.run_id if hasattr(continued_response, 'run_id') else None,
                "message": "Run completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error continuing paused run: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to continue paused run"
            }
