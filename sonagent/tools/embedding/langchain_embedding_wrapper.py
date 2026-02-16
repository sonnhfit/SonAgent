"""
LangChain Embedding Wrapper - Provides a unified interface for embedding models
that can use either LangChain's OpenAIEmbeddings or custom embedding implementations.
"""
import logging
import os
from typing import List, Optional

from .embedding import Embedding

logger = logging.getLogger(__name__)


class LangChainEmbeddingWrapper(Embedding):
    """Wrapper for embedding models that can use either LangChain's OpenAIEmbeddings or custom implementations."""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize the embedding wrapper.
        
        Args:
            config: Configuration dictionary with embedding settings
        """
        super().__init__(embedding_type="langchain_wrapper")
        self.config = config or {}
        self._embedding = None
        self._embedding_type = None
        
    def _initialize_embedding(self):
        """Initialize the embedding model based on available libraries and configuration."""
        if self._embedding is not None:
            return
            
        llm_config = self.config.get('llm', {})
        api_type = llm_config.get('api_type', 'openai')
        
        # Check if we have the required API key
        if api_type == 'openai' and not os.environ.get('OPENAI_API_KEY'):
            logger.warning("OPENAI_API_KEY not found in environment variables")
            self._embedding = None
            self._embedding_type = 'none'
            return
            
        # Try to use LangChain's OpenAIEmbeddings if available
        if api_type == 'openai':
            try:
                from langchain_openai import OpenAIEmbeddings
                
                # Get model from config or use default
                model = llm_config.get('embedding_model', 'text-embedding-3-small')
                
                # Get base_url for Azure OpenAI if specified
                base_url = llm_config.get('base_url')
                
                # Create embeddings instance
                embedding_kwargs = {
                    'model': model,
                }
                
                if base_url:
                    embedding_kwargs['base_url'] = base_url
                
                self._embedding = OpenAIEmbeddings(**embedding_kwargs)
                self._embedding_type = 'langchain'
                logger.info(f"Using LangChain OpenAIEmbeddings with model: {model}")
                return
            except ImportError as e:
                logger.warning(f"LangChain OpenAIEmbeddings not available: {e}")
        
        # Fall back to custom OAIEmbedding for OpenAI
        if api_type == 'openai':
            try:
                from .openai_embedding import OAIEmbedding
                self._embedding = OAIEmbedding()
                self._embedding_type = 'custom'
                logger.info("Using custom OAIEmbedding for embeddings (LangChain not available)")
                return
            except ImportError as e:
                logger.error(f"Custom OAIEmbedding not available: {e}")
        
        # No embedding model available
        self._embedding = None
        self._embedding_type = 'none'
        logger.warning("No embedding model available")
    
    def embed(self, text: str):
        """
        Embed a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        self._initialize_embedding()
        if not self._embedding:
            raise ValueError("No embedding model available. Check configuration and API keys.")
            
        if self._embedding_type == 'langchain':
            return self._embedding.embed_query(text)
        elif self._embedding_type == 'custom':
            return self._embedding.embed(text)
        else:
            raise ValueError(f"Unsupported embedding type: {self._embedding_type}")
    
    def embed_batch(self, texts: List[str]):
        """
        Embed multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        self._initialize_embedding()
        if not self._embedding:
            raise ValueError("No embedding model available. Check configuration and API keys.")
            
        if self._embedding_type == 'langchain':
            return self._embedding.embed_documents(texts)
        elif self._embedding_type == 'custom':
            # Check if custom implementation has embed_batch method
            if hasattr(self._embedding, 'embed_batch'):
                return self._embedding.embed_batch(texts)
            else:
                # Fall back to sequential embedding
                return [self._embedding.embed(text) for text in texts]
        else:
            raise ValueError(f"Unsupported embedding type: {self._embedding_type}")
    
    def is_available(self):
        """
        Check if embedding model is available.
        
        Returns:
            True if embedding model is available, False otherwise
        """
        self._initialize_embedding()
        return self._embedding is not None
    
    def get_embedding_type(self):
        """
        Get the type of embedding model being used.
        
        Returns:
            Embedding type as string: 'langchain', 'custom', or 'none'
        """
        self._initialize_embedding()
        return self._embedding_type


# Factory function for easy creation
def create_embedding_wrapper(config: Optional[dict] = None) -> LangChainEmbeddingWrapper:
    """
    Create an embedding wrapper instance.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        LangChainEmbeddingWrapper instance
    """
    return LangChainEmbeddingWrapper(config)