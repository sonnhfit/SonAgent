import logging
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from sqlalchemy import (JSON, BigInteger, DateTime, Integer, SmallInteger,
                        String, Text, Float, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import select

from sonagent.persistence.base import ModelBase, SessionType
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class Task(ModelBase):
    __tablename__ = "tasks"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default='pending')
    priority: Mapped[int] = mapped_column(SmallInteger, default=0)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # Execution data fields
    execution_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    total_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    challenge: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    execution_data: Mapped[Optional[str]] = mapped_column(String(10000), nullable=True)
    last_execution_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_execution_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=dt_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=dt_now, onupdate=dt_now)

    @staticmethod
    def get_all_tasks() -> List["Task"]:
        return Task.session.scalars(select(Task)).all()
    
    @staticmethod
    def get_task_by_id(task_id: int) -> "Task":
        return Task.session.scalars(
            select(Task).filter(Task.id == task_id)).one()
    
    @staticmethod
    def get_tasks_by_status(status: str) -> List["Task"]:
        return Task.session.scalars(
            select(Task).filter(Task.status == status)).all()
    
    @staticmethod
    def get_tasks_by_agent_id(agent_id: str) -> List["Task"]:
        return Task.session.scalars(
            select(Task).filter(Task.agent_id == agent_id)).all()
    
    @staticmethod
    def get_pending_tasks(limit: Optional[int] = None) -> List["Task"]:
        query = select(Task).filter(Task.status == 'pending').order_by(Task.priority.desc(), Task.created_at.asc())
        if limit:
            query = query.limit(limit)
        return Task.session.scalars(query).all()
    
    @staticmethod
    def get_in_progress_tasks() -> List["Task"]:
        return Task.session.scalars(
            select(Task).filter(Task.status == 'in_progress')).all()
    
    @staticmethod
    def create_task(agent_id: str, content: str, priority: int = 0, 
                   payload: Optional[Dict[str, Any]] = None,
                   scheduled_at: Optional[datetime] = None,
                   cron_expression: Optional[str] = None) -> "Task":
        task = Task(
            agent_id=agent_id,
            content=content,
            priority=priority,
            payload=payload,
            scheduled_at=scheduled_at,
            cron_expression=cron_expression,
            status='pending'
        )
        Task.session.add(task)
        Task.session.commit()
        return task
    
    def start(self) -> None:
        self.status = 'in_progress'
        self.started_at = dt_now()
        self.retry_count += 1
        Task.session.commit()
    
    def complete(self, result: Optional[Dict[str, Any]] = None) -> None:
        self.status = 'done'
        self.completed_at = dt_now()
        if result:
            self.result = result
        Task.session.commit()
    
    def fail(self, error_message: Optional[str] = None) -> None:
        self.status = 'failed'
        self.completed_at = dt_now()
        if error_message:
            self.result = {'error': error_message}
        Task.session.commit()
    
    def cancel(self) -> None:
        self.status = 'cancelled'
        self.completed_at = dt_now()
        Task.session.commit()
    
    def retry(self) -> bool:
        if self.retry_count < self.max_retries:
            self.status = 'pending'
            self.started_at = None
            self.completed_at = None
            Task.session.commit()
            return True
        return False
    
    def update_execution_data(self, tokens_used: int, duration_seconds: Optional[float] = None,
                            success: bool = True) -> None:
        """
        Update task execution statistics after a task execution.
        
        Args:
            tokens_used: Number of tokens used in this execution
            duration_seconds: Duration of execution in seconds (optional)
            success: Whether the execution was successful
        """
        # Update execution count
        current_count = self.execution_count or 0
        self.execution_count = current_count + 1
        
        # Update total tokens
        current_tokens = self.total_tokens_used or 0
        self.total_tokens_used = current_tokens + tokens_used
        
        # Update last execution tokens
        self.last_execution_tokens = tokens_used
        
        # Update last execution duration if provided
        if duration_seconds is not None:
            self.last_execution_duration = duration_seconds
        
        # Update success rate
        if self.execution_count > 0:
            current_success_count = (self.success_rate or 0.0) * (self.execution_count - 1) if self.success_rate else 0
            new_success_count = current_success_count + (1 if success else 0)
            self.success_rate = new_success_count / self.execution_count
        
        Task.session.commit()
    
    def get_task_value_score(self, discount_factor: float = 0.7,
                           short_term_weight: float = 0.3,
                           long_term_weight: float = 0.7) -> float:
        """
        Calculate task value score considering short-term and long-term goals.
        
        Args:
            discount_factor: Discount factor for future value (γ in RL)
            short_term_weight: Weight for short-term value
            long_term_weight: Weight for long-term value
            
        Returns:
            Task value score (higher is better)
        """
        # Base score from priority
        priority_score = self.priority * 10
        
        # Short-term value: based on estimated completion time and tokens
        short_term_value = 0.0
        if self.last_execution_tokens:
            # Lower tokens = faster completion = higher short-term value
            short_term_value = 100.0 / (self.last_execution_tokens + 1)
        
        # Long-term value: based on learning potential from challenge annotation
        long_term_value = 0.0
        if self.challenge:
            # Expert-annotated challenge levels have different long-term values
            challenge_values = {
                "easy": 10.0,
                "medium": 30.0,
                "hard": 60.0,
                "expert": 90.0
            }
            long_term_value = challenge_values.get(self.challenge.lower(), 0.0)
        
        # Apply discount factor to long-term value
        discounted_long_term = long_term_value * discount_factor
        
        # Combine scores
        total_value = (
            priority_score +
            short_term_value * short_term_weight +
            discounted_long_term * long_term_weight
        )
        
        return total_value
    
    def get_estimated_tokens(self) -> int:
        """
        Estimate tokens needed for next execution based on historical data.
        
        Returns:
            Estimated token count
        """
        if self.last_execution_tokens:
            return self.last_execution_tokens
        elif self.execution_count and self.execution_count > 0 and self.total_tokens_used:
            return int(self.total_tokens_used / self.execution_count)
        else:
            # Default estimate for new tasks
            return 1000


class Target(ModelBase):
    """
    Target/Objective model for system goals.
    Implements three-tier objective system:
    - Baseline objectives (survival, stability)
    - Strategic objectives (long-term goals)
    - Tactical objectives (short-term goals)
    """
    __tablename__ = "targets"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target: Mapped[str] = mapped_column(String(2000), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Current progress (0-100)
    progress: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='active')
    
    # Dates
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=dt_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=dt_now, onupdate=dt_now)
