import logging
from datetime import datetime
from typing import ClassVar, List, Optional

from sqlalchemy import (Integer, String, select)
from sqlalchemy.orm import (Mapped, mapped_column)

from sonagent.persistence.base import ModelBase, SessionType
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class Belief(ModelBase):
    __tablename__ = "belief"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String, nullable=False, unique=True)
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
            select(Belief).filter(Belief.id.in_(ids)).order_by(Belief.create_date.asc())).all()


