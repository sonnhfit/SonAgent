"""
Chat models for storing conversation history.
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Index
from sqlalchemy.ext.declarative import declared_attr

from sonagent.persistence.base import ModelBase
from sonagent.utils.datetime_helpers import dt_now


class ChatMessage(ModelBase):
    """
    Model for storing chat messages in conversations.
    """
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    message_metadata = Column(Text)  # JSON string for additional metadata
    created_at = Column(DateTime, default=dt_now)
    updated_at = Column(DateTime, default=dt_now, onupdate=dt_now)
    
    # Index for faster queries
    __table_args__ = (
        Index('ix_chat_messages_conversation_created', 'conversation_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"
    
    @classmethod
    def create_message(cls, conversation_id: str, role: str, content: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> 'ChatMessage':
        """
        Create a new chat message.
        
        Args:
            conversation_id: Unique identifier for the conversation
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Additional metadata as dictionary
            
        Returns:
            ChatMessage instance
        """
        message = cls(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_metadata=json.dumps(metadata) if metadata else None
        )
        cls.session.add(message)
        cls.session.commit()
        return message
    
    @classmethod
    def get_conversation_messages(cls, conversation_id: str, limit: int = 100, 
                                 offset: int = 0) -> list['ChatMessage']:
        """
        Get messages for a specific conversation.
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return
            offset: Offset for pagination
            
        Returns:
            List of ChatMessage objects
        """
        return cls.session.query(cls).filter(
            cls.conversation_id == conversation_id
        ).order_by(cls.created_at.asc()).offset(offset).limit(limit).all()
    
    @classmethod
    def get_recent_conversations(cls, limit: int = 20) -> list[str]:
        """
        Get list of recent conversation IDs.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation IDs
        """
        # Use distinct and group by to get unique conversation IDs
        results = cls.session.query(cls.conversation_id).distinct().order_by(
            cls.created_at.desc()
        ).limit(limit).all()
        return [r[0] for r in results]
    
    @classmethod
    def delete_conversation(cls, conversation_id: str) -> int:
        """
        Delete all messages in a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Number of messages deleted
        """
        count = cls.session.query(cls).filter(
            cls.conversation_id == conversation_id
        ).delete()
        cls.session.commit()
        return count
    
    @classmethod
    def get_message_count(cls, conversation_id: Optional[str] = None) -> int:
        """
        Get total message count, optionally filtered by conversation.
        
        Args:
            conversation_id: Optional conversation identifier
            
        Returns:
            Number of messages
        """
        query = cls.session.query(cls)
        if conversation_id:
            query = query.filter(cls.conversation_id == conversation_id)
        return query.count()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert message to dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        result = {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if self.message_metadata:
            try:
                result['metadata'] = json.loads(self.message_metadata)
            except json.JSONDecodeError:
                result['metadata'] = self.message_metadata
        
        return result


class Conversation(ModelBase):
    """
    Model for conversation metadata (optional, for additional conversation info).
    """
    __tablename__ = 'conversations'
    
    id = Column(String(255), primary_key=True)  # Same as conversation_id in ChatMessage
    title = Column(String(255))
    conversation_metadata = Column(Text)  # JSON string for additional metadata
    created_at = Column(DateTime, default=dt_now)
    updated_at = Column(DateTime, default=dt_now, onupdate=dt_now)
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title})>"
    
    @classmethod
    def create_or_update(cls, conversation_id: str, title: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> 'Conversation':
        """
        Create or update a conversation.
        
        Args:
            conversation_id: Conversation identifier
            title: Conversation title
            metadata: Additional metadata
            
        Returns:
            Conversation instance
        """
        conversation = cls.session.query(cls).filter(cls.id == conversation_id).first()
        
        if conversation:
            # Update existing
            if title is not None:
                conversation.title = title
            if metadata is not None:
                conversation.conversation_metadata = json.dumps(metadata)
            conversation.updated_at = dt_now()
        else:
            # Create new
            conversation = cls(
                id=conversation_id,
                title=title,
                conversation_metadata=json.dumps(metadata) if metadata else None
            )
            cls.session.add(conversation)
        
        cls.session.commit()
        return conversation
    
    @classmethod
    def get_conversation(cls, conversation_id: str) -> Optional['Conversation']:
        """
        Get conversation by ID.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Conversation instance or None if not found
        """
        return cls.session.query(cls).filter(cls.id == conversation_id).first()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert conversation to dictionary.
        
        Returns:
            Dictionary representation of the conversation
        """
        result = {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if self.conversation_metadata:
            try:
                result['metadata'] = json.loads(self.conversation_metadata)
            except json.JSONDecodeError:
                result['metadata'] = self.conversation_metadata
        
        return result
