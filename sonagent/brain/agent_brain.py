"""
AgentBrain - Core reasoning engine for SonAgent.
Implements dynamic skill loading, search, and chat history persistence.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sonagent.skills.skills_manager import SkillsManager
from sonagent.tools.embedding.langchain_embedding_wrapper import create_embedding_wrapper
from sonagent.tools.vector_database.vectordb import VectorDB
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


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
        import uuid
        import time
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
        if self.skills_loaded:
            return
            
        # Clear existing skill indices
        try:
            self.vector_db.delete_collection(self.skill_search_collection)
            self.vector_db.delete_collection(self.skill_keyword_collection)
        except:
            pass
            
        # Get all skills
        skills = self.skills_manager.get_all_skills()
        
        # Index skills for semantic search
        if self.embedding:
            self._index_skills_semantic(skills)
        
        # Index skills for keyword search
        self._index_skills_keywords(skills)
        
        self.skills_loaded = True
        logger.info(f"Loaded and indexed {len(skills)} skills")
    
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
                    'timestamp': dt_now()
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
                    'timestamp': dt_now()
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
        
        # Add timestamp to metadata
        metadata['timestamp'] = dt_now()
        
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
            'timestamp': dt_now()
        }
        
        # Save assistant response
        self.save_chat_message("assistant", response['response'])
        
        return response
    
    def reload_skills(self):
        """Reload and reindex skills."""
        self.skills_manager.reload_skills()
        self.load_and_index_skills()
        logger.info("Skills reloaded and reindexed")