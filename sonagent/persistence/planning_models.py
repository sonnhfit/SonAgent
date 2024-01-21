import logging
from sonagent.persistence.base import ModelBase, SessionType
from typing import Any, ClassVar, Dict, List, Optional, Sequence, cast
from sonagent.utils.datetime_helpers import dt_now

from sqlalchemy import (
    Enum,
    Float,
    ForeignKey,
    Integer,
    ScalarResult,
    Select,
    String,
    UniqueConstraint,
    desc,
    func,
    select,
)
from sqlalchemy.orm import Mapped, lazyload, mapped_column, relationship, validates


logger = logging.getLogger(__name__)


class Plan(ModelBase):
    __tablename__ = "plan"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal: Mapped[str] = mapped_column(String, nullable=False)
    subtask: Mapped[str] = mapped_column(String, nullable=True)
    info: Mapped[str] = mapped_column(String, nullable=True)
    is_done: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(String, nullable=True, default=dt_now)

    @staticmethod
    def get_all_plans(*, created_at: Optional[str] = None) -> List["Plan"]:
        return Plan.session.scalars(
            select(Plan).filter()).all()
    
    @staticmethod
    def get_plan_by_id(id: int) -> "Plan":
        return Plan.session.scalars(
            select(Plan).filter(Plan.id == id)).one()
    
    @staticmethod
    def get_plan_by_ids(ids: List[int]) -> List["Plan"]:
        return Plan.session.scalars(
            select(Plan).filter(Plan.id.in_(ids)).order_by(Plan.created_at.asc())).all()
