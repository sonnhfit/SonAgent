import logging
from sonagent.persistence.base import ModelBase, SessionType
from sonagent.utils.datetime_helpers import dt_now
from typing import Any, ClassVar, Dict, List, Optional, Sequence, cast

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
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class Belief(ModelBase):
    __tablename__ = "belief"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    create_date: Mapped[datetime] = mapped_column(nullable=True, default=dt_now)
    # is_still_belief: Mapped[bool] = mapped_column(nullable=False, default=True)

    @staticmethod
    def get_all_belief(*, create_date: Optional[datetime] = None) -> List["Belief"]:
        return Belief.session.scalars(
            select(Belief).filter()).all()

    @staticmethod
    def get_belief_by_id(id: int) -> "Belief":
        return Belief.session.scalars(
            select(Belief).filter(Belief.id == id)).one()
    
    @staticmethod
    def get_belief_by_ids(ids: List[int]) -> List["Belief"]:
        return Belief.session.scalars(
            select(Belief).filter(Belief.id.in_(ids))).all()


    def apply_sync(self, *args, **kwargs):
        """
        Load the belief to the agent memory.
        make sure data in db is synced with memory
        """
        pass

