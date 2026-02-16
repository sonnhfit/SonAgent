import logging
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from sqlalchemy import (JSON, BigInteger, DateTime, Integer, SmallInteger,
                        String, Text)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import select

from sonagent.persistence.base import ModelBase, SessionType
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class Task(ModelBase):
    __tablename__ = "tasks"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default='pending')
    priority: Mapped[int] = mapped_column(SmallInteger, default=0)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
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
                   scheduled_at: Optional[datetime] = None) -> "Task":
        task = Task(
            agent_id=agent_id,
            content=content,
            priority=priority,
            payload=payload,
            scheduled_at=scheduled_at,
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