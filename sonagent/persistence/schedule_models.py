import logging
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Dict, List, Optional, Sequence, cast

from sqlalchemy import (Enum, Float, ForeignKey, Integer, ScalarResult, Select,
                        String, UniqueConstraint, desc, func, select)
from sqlalchemy.orm import (Mapped, lazyload, mapped_column, relationship,
                            validates)

from sonagent.persistence.base import ModelBase, SessionType
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class ScheduleJob(ModelBase):
    __tablename__ = "schedule_job"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)
    max_retry: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    plan: Mapped[str] = mapped_column(String(1024), nullable=True)
    schedule_start_at: Mapped[datetime] = mapped_column(nullable=True, default=None)
    schedule_end_at: Mapped[datetime] = mapped_column(nullable=True, default=None)
    schedule_interval: Mapped[str] = mapped_column(nullable=True)
    last_run_at: Mapped[datetime] = mapped_column(nullable=True, default=None)
    next_run_at: Mapped[datetime] = mapped_column(nullable=True, default=None)
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "completed", "failed", name="job_status"),
        nullable=False,
        default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(nullable=True, default=dt_now)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=dt_now, onupdate=dt_now
    )

    @validates("is_recurring")
    def validate_is_recurring(self, key, value):
        if not isinstance(value, bool):
            raise ValueError("is_recurring must be a boolean value")
        return value

    @validates("max_retry")
    def validate_max_retry(self, key, value):
        if not isinstance(value, int) or value < 0:
            raise ValueError("max_retry must be a non-negative integer")
        return value
    
    @staticmethod
    def get_all_schedule_not_completed_jobs(*, created_at: Optional[str] = None) -> List["ScheduleJob"]:
        return ScheduleJob.session.scalars(
            select(ScheduleJob).filter(ScheduleJob.status != "completed")).all()
    
    @staticmethod
    def update_schedule_job_status(job_id: int, status: str) -> None:
        ScheduleJob.session.execute(
            ScheduleJob.update().where(ScheduleJob.id == job_id).values(status=status)
        )
        next_run_at = dt_now() + timedelta(minutes=10)
        ScheduleJob.session.execute(
            ScheduleJob.update().where(ScheduleJob.id == job_id).values(status=status, next_run_at=next_run_at)
        )

    @staticmethod
    def get_job_with_next_run_at_now() -> List["ScheduleJob"]:
        now = dt_now()
        sql = select(ScheduleJob).filter(ScheduleJob.next_run_at <= now).order_by(
                desc(ScheduleJob.next_run_at)
        )
        return ScheduleJob.session.scalars(
            sql).all()
