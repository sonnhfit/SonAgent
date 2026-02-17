"""
AgentBrain - Core reasoning engine for SonAgent.
Implements dynamic skill loading, search, chat history persistence, and ReAct agent.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sonagent.skills.skills_manager import SkillsManager
from sonagent.tools.embedding.langchain_embedding_wrapper import \
    create_embedding_wrapper
from sonagent.tools.vector_database.vectordb import VectorDB
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)

# Methods to skip when converting skills to tools (Pydantic and common BaseModel methods)
SKIP_METHODS = {
    # Pydantic v1 methods
    'construct', 'from_orm', 'dict', 'json', 'copy', 'validate', 
    'parse_obj', 'parse_raw', 'parse_file', 'schema', 'schema_json', 'update_forward_refs',
    # Pydantic v2 methods
    'model_construct', 'model_validate', 'model_validate_json', 'model_validate_strings',
    'model_dump', 'model_dump_json', 'model_copy', 'model_json_schema',
    'model_parametrized_name', 'model_post_init', 'model_rebuild',
    # Other common methods to skip
    'get', 'set', 'values', 'keys', 'items'
}

# Maximum context length threshold before triggering truncation
MAX_CONTEXT_TOKENS = 120000  # Leave 8000 tokens buffer for response

# Number of recent messages to always keep
RECENT_MESSAGES_TO_KEEP = 15

# LangChain imports for ReAct agent
try:
    from langchain.agents import create_agent
    from langchain.tools import BaseTool
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LangChain imports failed: {e}")
    LANGCHAIN_AVAILABLE = False


class AgentBrain:
    """Core brain implementation for SonAgent."""
    
    def __init__(self, config: Dict[str, Any], skills_manager: SkillsManager, conversation_id: str = None):
        """
        Initialize the AgentBrain.
        
        Args:
            config: Configuration dictionary
            skills_manager: SkillsManager instance for skill management
            conversation_id: Optional conversation ID to use (generates new one if not provided)
        """
        self.config = config
        self.skills_manager = skills_manager
        
        # Initialize memory and embedding for skill search only
        self.memory_path = config.get('memory_path', 'user_data/memory')
        self.vector_db = VectorDB(self.memory_path)
        
        # Initialize embedding wrapper for skill search
        self.embedding = create_embedding_wrapper(config)
        
        # Skill search collections (vector DB for skills only)
        self.skill_search_collection = "skill_search"
        self.skill_keyword_collection = "skill_keywords"
        
        # Global conversation ID for consistent chat context
        # Use provided conversation_id or generate a new one
        self.conversation_id = conversation_id if conversation_id else self._generate_conversation_id()
        
        # Initialize collections
        self._init_collections()
        
        # Load and index skills
        self.skills_loaded = False
        self.load_and_index_skills()
        
        logger.info(f"AgentBrain initialized successfully with conversation_id: {self.conversation_id}")
    
    def _check_openai_config(self) -> bool:
        """Check if OpenAI configuration is available."""
        llm_config = self.config.get('llm', {})
        return llm_config.get('api_type') == 'openai' and os.environ.get('OPENAI_API_KEY')
    
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
    
    def _init_collections(self):
        """Initialize vector database collections."""
        # Create collections if they don't exist
        try:
            self.vector_db.get_collection(self.chat_history_collection)
        except:
            pass  # Collection will be created on first use
            
        try:
            self.vector_db.get_collection(self.skill_search_collection)
        except:
            pass
            
        try:
            self.vector_db.get_collection(self.skill_keyword_collection)
        except:
            pass
    
    def load_and_index_skills(self):
        """Load skills from skills manager and index them for search."""
        logger.info("Loading and indexing skills...")
        
        if self.skills_loaded:
            logger.debug("Skills already loaded, skipping")
            return
            
        # Clear existing skill indices
        try:
            self.vector_db.delete_collection(self.skill_search_collection)
            self.vector_db.delete_collection(self.skill_keyword_collection)
        except:
            pass
            
        # Get all skills
        skills = self.skills_manager.get_all_skills()
        logger.info(f"Loaded {len(skills)} skills from skills directory")
        
        # Log each skill name for debugging
        for skill in skills:
            skill_name = skill.__class__.__name__
            logger.debug(f"  - Skill loaded: {skill_name}")
        
        # Index skills for semantic search
        if self.embedding:
            logger.info("Creating embeddings for skill search...")
            self._index_skills_semantic(skills)
        else:
            logger.warning("Embedding not available, skipping semantic indexing")
        
        # Index skills for keyword search
        self._index_skills_keywords(skills)
        
        self.skills_loaded = True
        logger.info(f"Skill loading and indexing complete")
    
    def _index_skills_semantic(self, skills: List[Any]):
        """Index skills for semantic/embedding-based search."""
        embeddings = []
        metadatas = []
        docs = []
        ids = []
        
        # Check if embedding is available
        if not self.embedding or not self.embedding.is_available():
            logger.warning("Embedding not available, skipping semantic indexing")
            return
            
        for i, skill in enumerate(skills):
            skill_name = skill.__class__.__name__
            skill_doc = skill.__doc__ or ""
            
            # Create skill description for embedding
            skill_description = f"{skill_name}: {skill_doc}"
            
            # Generate embedding
            try:
                embedding = self.embedding.embed(skill_description)
                embeddings.append(embedding)
                metadatas.append({
                    'skill_name': skill_name,
                    'type': 'semantic',
                    'timestamp': dt_now().isoformat()  # Convert to ISO format string for JSON serialization
                })
                docs.append(skill_description)
                ids.append(f"semantic_{skill_name}_{i}")
            except Exception as e:
                logger.error(f"Failed to generate embedding for skill {skill_name}: {e}")
        
        if embeddings:
            self.vector_db.add(
                embeddings=embeddings,
                metadatas=metadatas,
                docs=docs,
                ids=ids,
                collection=self.skill_search_collection
            )
    
    def _index_skills_keywords(self, skills: List[Any]):
        """Index skills for keyword-based search."""
        embeddings = []
        metadatas = []
        docs = []
        ids = []
        
        for i, skill in enumerate(skills):
            skill_name = skill.__class__.__name__
            skill_doc = skill.__doc__ or ""
            
            # Extract keywords from skill name and doc
            keywords = self._extract_keywords(f"{skill_name} {skill_doc}")
            
            for keyword in keywords:
                # For keyword search, we can use simple text matching or create keyword embeddings
                # For now, we'll store keywords as documents for text search
                metadatas.append({
                    'skill_name': skill_name,
                    'keyword': keyword,
                    'type': 'keyword',
                    'timestamp': dt_now().isoformat()  # Convert to ISO format string for JSON serialization
                })
                docs.append(keyword)
                ids.append(f"keyword_{skill_name}_{keyword}_{i}")
                
                # If we have embeddings, create keyword embeddings too
                if self.embedding:
                    try:
                        embedding = self.embedding.embed(keyword)
                        embeddings.append(embedding)
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for keyword {keyword}: {e}")
        
        if docs:
            # For keyword search without embeddings, we need a different approach
            # For now, we'll store them and implement keyword matching separately
            pass
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction - split by common separators and filter
        words = text.lower().split()
        keywords = []
        
        # Filter out common words and keep meaningful ones
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        for word in words:
            # Clean word
            word = word.strip('.,!?;:()[]{}"\'').strip()
            if word and len(word) > 2 and word not in stop_words:
                keywords.append(word)
        
        return list(set(keywords))  # Remove duplicates
    
    def search_skills(self, query: str, search_type: str = "semantic", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for skills based on query.
        
        Args:
            query: Search query
            search_type: "semantic" for embedding-based search, "keyword" for keyword search
            limit: Maximum number of results
            
        Returns:
            List of skill information dictionaries
        """
        results = []
        
        if search_type == "semantic" and self.embedding and self.embedding.is_available():
            # Semantic search using embeddings
            try:
                query_embedding = self.embedding.embed(query)
                search_results = self.vector_db.query(
                    embedding=query_embedding,
                    k=limit,
                    collection=self.skill_search_collection
                )
                
                # Process results
                if search_results and 'metadatas' in search_results:
                    for i, metadata in enumerate(search_results['metadatas'][0]):
                        skill_name = metadata.get('skill_name', 'Unknown')
                        skill = self._get_skill_by_name(skill_name)
                        if skill:
                            results.append({
                                'skill': skill,
                                'skill_name': skill_name,
                                'score': search_results['distances'][0][i] if 'distances' in search_results else 0,
                                'type': 'semantic'
                            })
            except Exception as e:
                logger.error(f"Semantic search failed: {e}")
        
        elif search_type == "keyword":
            # Keyword search - simpler text matching
            query_keywords = self._extract_keywords(query)
            skills = self.skills_manager.get_all_skills()
            
            for skill in skills:
                skill_name = skill.__class__.__name__
                skill_doc = skill.__doc__ or ""
                skill_text = f"{skill_name} {skill_doc}".lower()
                
                # Count keyword matches
                match_count = sum(1 for keyword in query_keywords if keyword in skill_text)
                if match_count > 0:
                    results.append({
                        'skill': skill,
                        'skill_name': skill_name,
                        'score': match_count,
                        'type': 'keyword'
                    })
            
            # Sort by match count
            results.sort(key=lambda x: x['score'], reverse=True)
            results = results[:limit]
        
        return results
    
    def _get_skill_by_name(self, skill_name: str) -> Optional[Any]:
        """Get skill object by name."""
        skills = self.skills_manager.get_all_skills()
        for skill in skills:
            if skill.__class__.__name__ == skill_name:
                return skill
        return None
    
    def save_chat_message(self, role: str, content: str, metadata: Optional[Dict] = None, 
                         conversation_id: str = None):
        """
        Save a chat message to ChatMessage model in persistence.
        
        Args:
            role: "user" or "assistant"
            content: Message content
            metadata: Additional metadata
            conversation_id: Conversation identifier (uses global conversation_id if not provided)
        """
        if metadata is None:
            metadata = {}
        
        # Use global conversation_id if not provided
        if conversation_id is None:
            conversation_id = self.conversation_id
        
        # Add timestamp to metadata - convert datetime to ISO format string for JSON serialization
        metadata['timestamp'] = dt_now().isoformat()
        
        try:
            # Import locally to avoid circular imports
            from sonagent.persistence import ChatMessage

            # Save to ChatMessage model
            ChatMessage.create_message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                metadata=metadata
            )
            logger.debug(f"Chat message saved to persistence (conversation_id: {conversation_id}): {role}: {content[:50]}...")
        except Exception as e:
            logger.error(f"Failed to save chat message to persistence: {e}")
    
    def get_chat_history(self, limit: int = 20, conversation_id: str = None) -> List[Dict[str, Any]]:
        """
        Get chat history from persistence.
        
        Args:
            limit: Maximum number of messages to return
            conversation_id: Conversation identifier (uses global conversation_id if not provided)
            
        Returns:
            List of chat messages with metadata
        """
        # Use global conversation_id if not provided
        if conversation_id is None:
            conversation_id = self.conversation_id
            
        try:
            # Import locally to avoid circular imports
            from sonagent.persistence import ChatMessage

            # Get messages for the conversation
            messages = ChatMessage.get_conversation_messages(
                conversation_id=conversation_id,
                limit=limit
            )
            
            # Convert to dictionary format
            history = []
            for message in messages:
                # Use to_dict() method which handles the metadata field correctly
                message_dict = message.to_dict()
                history.append({
                    'id': message_dict['id'],
                    'conversation_id': message_dict['conversation_id'],
                    'role': message_dict['role'],
                    'content': message_dict['content'],
                    'created_at': message_dict['created_at'],
                    'metadata': message_dict.get('metadata', {})
                })
            
            logger.debug(f"Retrieved {len(history)} chat messages from persistence (conversation_id: {conversation_id})")
            return history
        except Exception as e:
            logger.error(f"Failed to get chat history from persistence: {e}")
            return []
    
    def clear_chat_history(self, conversation_id: str = None, start_new_conversation: bool = True):
        """
        Clear chat history for a specific conversation.
        
        Args:
            conversation_id: Conversation identifier (uses global conversation_id if not provided)
            start_new_conversation: Whether to start a new conversation after clearing (default: True)
        """
        # Use global conversation_id if not provided
        if conversation_id is None:
            conversation_id = self.conversation_id
            
        try:
            # Import locally to avoid circular imports
            from sonagent.persistence import ChatMessage

            # Delete messages for the conversation
            deleted_count = ChatMessage.delete_conversation(conversation_id)
            logger.info(f"Cleared {deleted_count} chat messages for conversation: {conversation_id}")
            
            # Start a new conversation by generating a new conversation_id
            if start_new_conversation:
                old_id = self.conversation_id
                self.conversation_id = self._generate_conversation_id()
                logger.info(f"Started new conversation: {old_id} -> {self.conversation_id}")
                
        except Exception as e:
            logger.error(f"Failed to clear chat history: {e}")
    
    def get_dynamic_tools(self, query: str = None) -> List[Any]:
        """
        Get dynamic tools based on current context or query.
        
        Args:
            query: Optional query to filter tools
            
        Returns:
            List of tool objects
        """
        if query:
            # Search for relevant skills
            search_results = self.search_skills(query, search_type="semantic", limit=10)
            tools = [result['skill'] for result in search_results]
        else:
            # Return all skills as tools
            tools = self.skills_manager.get_all_skills()
        
        return tools
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query using available skills.
        
        Args:
            query: User query
            
        Returns:
            Dictionary with response and metadata
        """
        # Save user message
        self.save_chat_message("user", query)
        
        # Search for relevant skills
        relevant_skills = self.search_skills(query, search_type="semantic", limit=3)
        
        # For now, return a simple response
        # In a full implementation, this would use an LLM to decide which skills to use
        response = {
            'query': query,
            'relevant_skills': [skill['skill_name'] for skill in relevant_skills],
            'response': f"I found {len(relevant_skills)} skills that might help with your query: {query}",
            'timestamp': dt_now().isoformat()  # Convert to ISO format string for JSON serialization
        }
        
        # Save assistant response
        self.save_chat_message("assistant", response['response'])
        
        return response
    
    def reload_skills(self):
        """Reload and reindex skills."""
        self.skills_manager.reload_skills()
        self.load_and_index_skills()
        logger.info("Skills reloaded and reindexed")
    
    def _convert_skill_to_tools(self, skill: Any) -> List[BaseTool]:
        """
        Convert a SonAgent skill to multiple LangChain Tools (one per method).
        
        Args:
            skill: SonAgent skill object
            
        Returns:
            List of LangChain Tool objects
        """
        skill_name = skill.__class__.__name__
        tools = []
        
        logger.debug(f"Converting skill '{skill_name}' to tools (all methods)")
        
        # Find all callable public methods
        for attr_name in dir(skill):
            # Skip private methods, special methods, and Pydantic methods
            if attr_name.startswith('_') or attr_name in SKIP_METHODS:
                continue
            
            attr = getattr(skill, attr_name)
            if not callable(attr):
                continue
            
            method_name = attr_name
            method = attr
            
            # Get the method's docstring if available
            method_doc = method.__doc__ or ""
            
            logger.debug(f"  Found callable method '{method_name}' in {skill_name}")
            
            # Create tool function using the tool decorator
            from langchain.tools import tool
            import inspect
            
            # Get method signature to include parameter info in description
            try:
                sig = inspect.signature(method)
                param_info = []
                for param_name, param in sig.parameters.items():
                    if param_name in ('self', 'cls'):
                        continue
                    if param.default == inspect.Parameter.empty:
                        param_info.append(f"{param_name} (required)")
                    else:
                        param_info.append(f"{param_name} (optional)")
                
                if param_info:
                    func_description = f"{method_doc.strip() if method_doc else f'Execute {skill_name}.{method_name}'}\n\nParameters: {', '.join(param_info)}"
                else:
                    func_description = method_doc.strip() if method_doc else f"Execute {skill_name}.{method_name}"
            except Exception:
                # Fallback to just docstring if signature inspection fails
                func_description = method_doc.strip() if method_doc else f"Execute {skill_name}.{method_name}"
            
            # Create a closure to capture the current method reference and description
            def make_tool_func(skill_instance, method_ref, skill_cls_name, method_nm, description):
                @tool(description=description)
                def skill_tool_func(**kwargs):
                    """Execute the skill method with provided arguments."""
                    try:
                        # Check for required arguments that might be missing
                        import inspect
                        sig = inspect.signature(method_ref)
                        missing_args = []
                        for param_name, param in sig.parameters.items():
                            if param.default == inspect.Parameter.empty and param_name not in kwargs:
                                missing_args.append(param_name)
                        
                        if missing_args:
                            return f"Error: Missing required arguments: {', '.join(missing_args)}. Please provide all required arguments."
                        
                        result = method_ref(**kwargs)
                        return str(result)
                    except TypeError as e:
                        if "missing" in str(e) and "required positional argument" in str(e):
                            return f"Error: {str(e)}. Please provide all required arguments."
                        error_msg = f"Error executing {skill_cls_name}.{method_nm}: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        return error_msg
                    except Exception as e:
                        error_msg = f"Error executing {skill_cls_name}.{method_nm}: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        return error_msg
                
                # Use underscore instead of dot to match OpenAI's required pattern: ^[a-zA-Z0-9_-]+$
                skill_tool_func.name = f"{skill_cls_name}_{method_nm}"
                return skill_tool_func
            
            tool_func = make_tool_func(skill, method, skill_name, method_name, func_description)
            tools.append(tool_func)
            logger.info(f"Created tool: {tool_func.name}")
        
        if not tools:
            logger.warning(f"No callable methods found for skill {skill_name}")
        
        return tools
    
    def _convert_skill_to_tool(self, skill: Any) -> BaseTool:
        """
        Convert a SonAgent skill to a LangChain Tool.
        
        Args:
            skill: SonAgent skill object
            
        Returns:
            LangChain Tool object
        """
        skill_name = skill.__class__.__name__
        skill_doc = skill.__doc__ or ""
        
        logger.debug(f"Converting skill to tool: {skill_name}")
        
        # Extract description from docstring
        description_lines = skill_doc.strip().split('\n')
        description = description_lines[0] if description_lines else f"Skill: {skill_name}"
        
        # Find the first method that's not __init__ or private
        # Skip Pydantic's 'construct' method and other special methods
        method_name = None
        method_doc = ""
        
        logger.debug(f"Searching for callable methods in {skill_name}")
        for attr_name in dir(skill):
            # Skip private methods and special Pydantic methods
            if attr_name.startswith('_') or attr_name in SKIP_METHODS:
                continue
            if callable(getattr(skill, attr_name)):
                method = getattr(skill, attr_name)
                # Get the method's docstring if available
                method_doc = method.__doc__ or ""
                method_name = attr_name
                logger.debug(f"Found callable method '{method_name}' in {skill_name}")
                break
        
        if not method_name:
            # Default to a generic call method
            logger.warning(f"No callable method found for skill {skill_name}, creating generic tool")
            def generic_skill_func(**kwargs):
                return f"Skill {skill_name} executed with args: {kwargs}"
            
            # Create a simple tool using the tool decorator
            from langchain.tools import tool
            
            @tool
            def tool_func(**kwargs):
                """Execute the skill with provided arguments."""
                return generic_skill_func(**kwargs)
            
            tool_func.name = skill_name
            tool_func.description = description
            return tool_func
        
        # Get the method
        method = getattr(skill, method_name)
        
        # Create tool function using the tool decorator
        from langchain.tools import tool
        
        # Use method docstring if available, otherwise use class description
        # Method docstring is more specific and detailed for the tool
        func_description = method_doc if method_doc else description
        
        @tool(description=func_description)
        def skill_tool_func(**kwargs):
            """Execute the skill with provided arguments."""
            try:
                result = method(**kwargs)
                return str(result)
            except Exception as e:
                return f"Error executing skill {skill_name}: {str(e)}"
        
        # Use underscore instead of dot to match OpenAI's required pattern: ^[a-zA-Z0-9_-]+$
        skill_tool_func.name = f"{skill_name}_{method_name}"
        logger.info(f"Created tool: {skill_tool_func.name} with description: {func_description[:100]}...")
        return skill_tool_func
    
    def _get_llm(self):
        """
        Get LLM instance based on configuration.
        
        Returns:
            LangChain LLM instance
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not available. Please install langchain package.")
        
        llm_config = self.config.get('llm', {})
        api_type = llm_config.get('api_type', 'openai')
        
        if api_type == 'openai':
            # Check for API key
            api_key = os.environ.get('OPENAI_API_KEY') or llm_config.get('api_key')
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable or configure in llm.api_key")
            
            model_name = llm_config.get('model', 'gpt-4o-mini')
            temperature = llm_config.get('temperature', 0.1)
            max_tokens = llm_config.get('max_tokens', 1000)
            
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
                timeout=30
            )
        else:
            raise ValueError(f"Unsupported LLM API type: {api_type}")
    
    def create_react_agent(self, tools: List[Any] = None, system_prompt: str = None) -> Any:
        """
        Create a ReAct agent with the specified tools.
        
        Args:
            tools: List of tools (skills) to use. If None, uses all available skills.
            system_prompt: Custom system prompt for the agent
            
        Returns:
            AgentExecutor instance
        """
        if not LANGCHAIN_AVAILABLE:
            logger.error("LangChain is not available. Cannot create ReAct agent.")
            return None
        
        try:
            # Get LLM
            llm = self._get_llm()
            
            logger.info(f"Creating ReAct agent with LLM: {llm.__class__.__name__}")
            
            # Convert skills to tools if not provided
            if tools is None:
                skills = self.skills_manager.get_all_skills()
                logger.info(f"No tools provided, loading all {len(skills)} skills")
                # Convert each skill to multiple tools (one per method)
                tools = []
                for skill in skills:
                    skill_tools = self._convert_skill_to_tools(skill)
                    tools.extend(skill_tools)
            else:
                # Convert provided skills to tools
                logger.info(f"Converting {len(tools)} provided tools")
                converted_tools = []
                for tool in tools:
                    if isinstance(tool, BaseTool):
                        converted_tools.append(tool)
                    else:
                        # Convert skill to multiple tools
                        skill_tools = self._convert_skill_to_tools(tool)
                        converted_tools.extend(skill_tools)
                tools = converted_tools
            
            logger.info(f"Total tools available for agent: {len(tools)}")
            for tool in tools:
                logger.debug(f"  - Tool: {tool.name}")
            
            # Handle empty tools list - agent can still work without tools
            if not tools:
                logger.warning("No tools available for ReAct agent. Creating agent without tools.")
                # Create a simple agent without tools
                # For LangChain 1.x, we can use create_agent even without tools
                # The create_agent function will handle it gracefully
                if system_prompt is None:
                    system_prompt = """You are SonAgent, an autonomous AI agent. 
                    Answer the user's question to the best of your ability."""
                
                # Create agent without tools
                agent = create_agent(
                    model=llm,
                    tools=[],  # Empty tools list
                    system_prompt=system_prompt
                )
                
                logger.info("Created ReAct agent without tools")
                return agent
            
            # Default system prompt for agent with tools
            if system_prompt is None:
                system_prompt = """You are SonAgent, an autonomous AI agent that can use tools to accomplish tasks.

You have access to the following tools:
{tools}

IMPORTANT INSTRUCTIONS FOR SKILL GENERATION:

When a user asks you to CREATE, GENERATE, or BUILD a new skill, you MUST use one of the SkillBuilder tools:

1. **SkillBuilder_create_simple_skill**: For creating a skill from a natural language description
   - Use this when the user provides a simple description of what they want
   - Parameters: skill_name (Python class name), prompt (what the skill should do)
   - Example: "create a skill to check weather" → call SkillBuilder_create_simple_skill with skill_name="WeatherChecker", prompt="Check the weather in a specified city"

2. **SkillBuilder_generate_skill**: For creating a detailed skill with specific parameters
   - Use this when you need precise control over the skill structure
   - Parameters: skill_name, description, method_name (optional), parameters (JSON string), implementation (optional Python code)
   - Example: For a calculator skill with add/subtract methods, specify the exact parameters

3. **SkillBuilder_test_skill_code**: For testing skill code before deploying
   - Use this to validate Python skill code
   - Parameters: code (Python code as string)

IMPORTANT RULES:
- When calling SkillBuilder tools, provide ALL required arguments as a valid JSON object
- skill_name must be a valid Python class name (PascalCase, no spaces)
- Always inform the user after successfully creating a skill that they need to reload skills
- If skill creation fails, explain the error to the user

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (MUST be a valid JSON string with all required arguments)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
            
            # Create ReAct agent using create_agent
            # The create_agent function handles the ReAct pattern internally
            agent = create_agent(
                model=llm,
                tools=tools,
                system_prompt=system_prompt
            )
            
            logger.info(f"Created ReAct agent with {len(tools)} tools")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create ReAct agent: {e}")
            return None
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for a given text.
        
        Uses a simple approximation: ~4 characters per token on average.
        This is a rough estimate but sufficient for context management.
        
        Args:
            text: Text to estimate token count for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        # Average of 4 characters per token
        return len(text) // 4
    
    def _estimate_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Estimate total token count for messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            Estimated total token count
        """
        total = 0
        for msg in messages:
            # Add role overhead (approximately 4 tokens per message for role)
            total += 4
            content = msg.get('content', '')
            total += self._estimate_token_count(content)
        return total
    
    def _truncate_messages(self, messages: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """
        Truncate messages to fit within token limit.
        
        Keeps recent messages and summarizes older ones if needed.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens allowed
            
        Returns:
            Truncated messages list
        """
        if not messages:
            return messages
        
        # First, try to keep recent messages only
        recent_messages = messages[-RECENT_MESSAGES_TO_KEEP:] if len(messages) > RECENT_MESSAGES_TO_KEEP else messages
        
        # Check if recent messages fit
        if self._estimate_messages_tokens(recent_messages) <= max_tokens:
            logger.info(f"Truncated to {len(recent_messages)} recent messages")
            return recent_messages
        
        # If still too large, return just the last few messages
        minimal_messages = messages[-5:] if len(messages) >= 5 else messages
        logger.warning(f"Very long context, using only {len(minimal_messages)} most recent messages")
        return minimal_messages
    
    def _summarize_old_messages(self, messages: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """
        Summarize old messages using LLM and keep recent messages.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens allowed
            
        Returns:
            Messages with old ones summarized
        """
        if len(messages) <= RECENT_MESSAGES_TO_KEEP:
            return messages
        
        # Split into old and recent
        recent_messages = messages[-RECENT_MESSAGES_TO_KEEP:]
        old_messages = messages[:-RECENT_MESSAGES_TO_KEEP]
        
        if not old_messages:
            return messages
        
        # Create a summary of old messages
        summary_content = self._create_messages_summary(old_messages)
        
        # Build new messages list with summary
        summarized_messages = [
            {
                'role': 'system',
                'content': f"Previous conversation summary: {summary_content}"
            }
        ]
        summarized_messages.extend(recent_messages)
        
        # Check if fits
        if self._estimate_messages_tokens(summarized_messages) <= max_tokens:
            logger.info(f"Created summary of {len(old_messages)} messages, keeping {len(recent_messages)} recent")
            return summarized_messages
        
        # If still too large, truncate more
        return self._truncate_messages(messages, max_tokens)
    
    def _create_messages_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        Create a brief summary of messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Summary string
        """
        if not messages:
            return "No previous messages."
        
        # Simple summary - just capture the key points
        user_messages = [msg['content'] for msg in messages if msg.get('role') == 'user']
        
        if len(user_messages) <= 3:
            # If few messages, just list them
            return f"User discussed: {'; '.join(user_messages[:5])}"
        
        # More than 3 messages - summarize
        summary = f"User had {len(user_messages)} previous interactions. "
        summary += f"Last few topics: {'; '.join(user_messages[-3:])}"
        
        return summary
    
    def _manage_context_length(self, messages: List[Dict[str, Any]], system_prompt: str = None) -> List[Dict[str, Any]]:
        """
        Manage context length by truncating or summarizing messages.
        
        Args:
            messages: List of message dictionaries
            system_prompt: Optional system prompt to include in token count
            
        Returns:
            Processed messages list that fits within token limit
        """
        # Calculate available token budget
        system_prompt_tokens = self._estimate_token_count(system_prompt or "") if system_prompt else 0
        # Reserve tokens for tools and response
        reserved_tokens = 2000
        available_tokens = MAX_CONTEXT_TOKENS - system_prompt_tokens - reserved_tokens
        
        current_tokens = self._estimate_messages_tokens(messages)
        
        logger.debug(f"Current context: ~{current_tokens} tokens, limit: {MAX_CONTEXT_TOKENS}")
        
        if current_tokens <= available_tokens:
            # Context is fine
            return messages
        
        logger.warning(f"Context too long ({current_tokens} > {available_tokens}), managing...")
        
        # First try truncation
        truncated = self._truncate_messages(messages, available_tokens)
        if self._estimate_messages_tokens(truncated) <= available_tokens:
            return truncated
        
        # If truncation not enough, try summarization
        return self._summarize_old_messages(messages, available_tokens)
    
    def _build_messages_from_history(self, chat_history: List[Dict[str, Any]], system_prompt: str = None) -> List[Dict[str, Any]]:
        """
        Build messages list from chat history for LangChain agent.
        
        Args:
            chat_history: List of chat message dictionaries from get_chat_history()
            system_prompt: Optional system prompt to manage context length
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        messages = []
        for msg in chat_history:
            role = msg.get('role', 'user')
            # Map 'assistant' to 'ai' for LangChain compatibility
            if role == 'assistant':
                role = 'ai'
            messages.append({
                'role': role,
                'content': msg.get('content', '')
            })
        
        # Manage context length if needed
        if len(messages) > 5:  # Only manage if we have enough messages
            messages = self._manage_context_length(messages, system_prompt)
        
        return messages
    
    def process_query_with_react(self, query: str, tools: List[Any] = None, system_prompt: str = None, 
                                  include_history: bool = True, history_limit: int = 20) -> Dict[str, Any]:
        """
        Process a user query using ReAct agent.
        
        Args:
            query: User query
            tools: List of tools to use (optional)
            system_prompt: Custom system prompt (optional)
            include_history: Whether to include conversation history (default: True)
            history_limit: Maximum number of history messages to include (default: 20)
            
        Returns:
            Dictionary with response and metadata
        """
        # Save user message
        self.save_chat_message("user", query)
        
        if not LANGCHAIN_AVAILABLE:
            response_text = "LangChain is not available. Please install langchain package to use ReAct agent."
            response = {
                'query': query,
                'response': response_text,
                'timestamp': dt_now().isoformat(),
                'error': 'LangChain not available'
            }
            self.save_chat_message("assistant", response_text)
            return response
        
        # Get default system prompt if not provided
        if system_prompt is None:
            system_prompt = """You are SonAgent, an autonomous AI agent that can use tools to accomplish tasks.

You have access to the following tools:
{tools}

IMPORTANT INSTRUCTIONS FOR SKILL GENERATION:

When a user asks you to CREATE, GENERATE, or BUILD a new skill, you MUST use one of the SkillBuilder tools:

1. **SkillBuilder_create_simple_skill**: For creating a skill from a natural language description
   - Use this when the user provides a simple description of what they want
   - Parameters: skill_name (Python class name), prompt (what the skill should do)
   - Example: "create a skill to check weather" → call SkillBuilder_create_simple_skill with skill_name="WeatherChecker", prompt="Check the weather in a specified city"

2. **SkillBuilder_generate_skill**: For creating a detailed skill with specific parameters
   - Use this when you need precise control over the skill structure
   - Parameters: skill_name, description, method_name (optional), parameters (JSON string), implementation (optional Python code)
   - Example: For a calculator skill with add/subtract methods, specify the exact parameters

3. **SkillBuilder_test_skill_code**: For testing skill code before deploying
   - Use this to validate Python skill code
   - Parameters: code (Python code as string)

IMPORTANT RULES:
- When calling SkillBuilder tools, provide ALL required arguments as a valid JSON object
- skill_name must be a valid Python class name (PascalCase, no spaces)
- Always inform the user after successfully creating a skill that they need to reload skills
- If skill creation fails, explain the error to the user

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (MUST be a valid JSON string with all required arguments)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
        
        try:
            # Create or get agent
            agent = self.create_react_agent(tools, system_prompt)
            
            if agent is None:
                response_text = "Failed to create ReAct agent."
                response = {
                    'query': query,
                    'response': response_text,
                    'timestamp': dt_now().isoformat(),
                    'error': 'Agent creation failed'
                }
                self.save_chat_message("assistant", response_text)
                return response
            
            # Get conversation history for context (with context management)
            messages = []
            if include_history:
                chat_history = self.get_chat_history(limit=history_limit)
                messages = self._build_messages_from_history(chat_history, system_prompt)
            
            # Add current user query to messages
            messages.append({"role": "user", "content": query})
            
            logger.info(f"Invoking ReAct agent with query: {query[:100]}...")
            logger.debug(f"Messages context: {len(messages)} messages")
            
            # Execute agent with conversation history using 'messages' parameter
            result = agent.invoke({"messages": messages})

            logger.info(f"ReAct agent raw result type: {type(result)}")
            logger.debug(f"ReAct agent raw result: {result}")
            
            # Extract response - handle different result formats
            response_text = None
            
            # Try 'output' key first (standard LangChain agent output)
            if 'output' in result:
                response_text = result.get('output')
            # Try 'messages' key (when agent has no tools or returns messages directly)
            elif 'messages' in result:
                messages = result.get('messages', [])
                if messages and len(messages) > 0:
                    # Get the last message content
                    last_message = messages[-1]
                    if hasattr(last_message, 'content'):
                        response_text = last_message.content
                    elif isinstance(last_message, dict):
                        response_text = last_message.get('content', 'No response generated')
            
            # Fallback if no response found
            if not response_text:
                response_text = 'No response generated'
            
            # Save response
            response = {
                'query': query,
                'response': response_text,
                'intermediate_steps': result.get('intermediate_steps', []),
                'timestamp': dt_now().isoformat()
            }
            
            self.save_chat_message("assistant", response_text)
            return response
            
        except Exception as e:
            error_str = str(e)
            
            # Check for context length error
            if 'context length' in error_str.lower() or 'contextlengthexceeded' in error_str.lower():
                logger.error(f"Context length exceeded, attempting retry with reduced history...")
                
                try:
                    # Retry with minimal context - only recent messages
                    messages = []
                    if include_history:
                        # Get only recent messages and force truncation
                        chat_history = self.get_chat_history(limit=5)
                        # Force minimal context
                        messages = self._truncate_messages(
                            self._build_messages_from_history(chat_history, system_prompt),
                            MAX_CONTEXT_TOKENS - 5000  # More aggressive limit for retry
                        )
                    
                    # Add current user query
                    messages.append({"role": "user", "content": query})
                    
                    logger.info(f"Retrying with {len(messages)} messages")
                    
                    # Create agent again (tools stay the same)
                    agent = self.create_react_agent(tools, system_prompt)
                    
                    if agent:
                        result = agent.invoke({"messages": messages})
                        
                        # Extract response
                        response_text = None
                        if 'output' in result:
                            response_text = result.get('output')
                        elif 'messages' in result:
                            msgs = result.get('messages', [])
                            if msgs and len(msgs) > 0:
                                last_msg = msgs[-1]
                                if hasattr(last_msg, 'content'):
                                    response_text = last_msg.content
                                elif isinstance(last_msg, dict):
                                    response_text = last_msg.get('content', 'No response generated')
                        
                        if not response_text:
                            response_text = 'No response generated'
                        
                        response = {
                            'query': query,
                            'response': response_text,
                            'intermediate_steps': result.get('intermediate_steps', []),
                            'timestamp': dt_now().isoformat(),
                            'retry': True
                        }
                        self.save_chat_message("assistant", response_text)
                        return response
                except Exception as retry_error:
                    logger.error(f"Retry also failed: {retry_error}")
            
            logger.error(f"Error in ReAct agent execution: {e}")
            response_text = f"Error processing query with ReAct agent: {str(e)}"
            response = {
                'query': query,
                'response': response_text,
                'timestamp': dt_now().isoformat(),
                'error': str(e)
            }
            self.save_chat_message("assistant", response_text)
            return response
    
    def get_dynamic_react_tools(self, query: str = None, limit: int = 5) -> List[BaseTool]:
        """
        Get dynamic tools for ReAct agent based on query relevance.
        
        Args:
            query: Query to find relevant tools
            limit: Maximum number of SKILLS to return (each skill may have multiple methods/tools)
            
        Returns:
            List of LangChain Tool objects
        """
        if query:
            # Search for relevant skills
            search_results = self.search_skills(query, search_type="semantic", limit=limit)
            skills = [result['skill'] for result in search_results]
        else:
            # Get all skills
            skills = self.skills_manager.get_all_skills()
            skills = skills[:limit]
        
        # Convert to tools (multiple tools per skill)
        tools = []
        for skill in skills:
            skill_tools = self._convert_skill_to_tools(skill)
            tools.extend(skill_tools)
        
        return tools
