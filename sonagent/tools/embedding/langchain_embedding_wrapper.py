"""
LangChain Embedding Wrapper - Provides a unified interface for embedding models
using LangChain's OpenAIEmbeddings with fallback to custom implementation.
"""
import logging
import os
from typing import List, Optional, Any, Dict

from .embedding import Embedding

logger = logging.getLogger(__name__)


class LangChainEmbeddingWrapper(Embedding):
    """Wrapper for embedding models using LangChain's OpenAIEmbeddings."""
    
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
            
        # Try to use LangChain's OpenAIEmbeddings as primary choice
        if api_type == 'openai':
            try:
                from langchain_openai import OpenAIEmbeddings
                
                # Get configuration parameters
                model = llm_config.get('embedding_model', 'text-embedding-3-small')
                base_url = llm_config.get('base_url')
                api_key = os.environ.get('OPENAI_API_KEY')
                organization = llm_config.get('organization')
                timeout = llm_config.get('timeout')
                max_retries = llm_config.get('max_retries')
                default_headers = llm_config.get('default_headers')
                
                # Create embeddings instance with all available parameters
                embedding_kwargs: Dict[str, Any] = {
                    'model': model,
                    'api_key': api_key,
                }
                
                # Add optional parameters if provided
                if base_url:
                    embedding_kwargs['base_url'] = base_url
                if organization:
                    embedding_kwargs['organization'] = organization
                if timeout is not None:
                    embedding_kwargs['timeout'] = timeout
                if max_retries is not None:
                    embedding_kwargs['max_retries'] = max_retries
                if default_headers:
                    embedding_kwargs['default_headers'] = default_headers
                
                self._embedding = OpenAIEmbeddings(**embedding_kwargs)
                self._embedding_type = 'langchain'
                logger.info(f"Using LangChain OpenAIEmbeddings with model: {model}")
                return
            except ImportError as e:
                logger.warning(f"LangChain OpenAIEmbeddings not available: {e}")
            except Exception as e:
                logger.error(f"Failed to initialize LangChain OpenAIEmbeddings: {e}")
        
        # Fall back to custom OAIEmbedding for OpenAI if LangChain fails
        if api_type == 'openai':
            try:
                from .openai_embedding import OAIEmbedding
                self._embedding = OAIEmbedding()
                self._embedding_type = 'custom'
                logger.info("Using custom OAIEmbedding for embeddings (LangChain not available)")
                return
            except ImportError as e:
                logger.error(f"Custom OAIEmbedding not available: {e}")
            except Exception as e:
                logger.error(f"Failed to initialize custom OAIEmbedding: {e}")
        
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