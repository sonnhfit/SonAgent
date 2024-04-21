import logging
from datetime import datetime, timedelta
from typing import ClassVar, List, Optional

from sqlalchemy import Enum, Integer, String, desc, select
from sqlalchemy.orm import Mapped, mapped_column, validates

from sonagent.persistence.base import ModelBase, SessionType
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class Environment(ModelBase):
    __tablename__ = "environment"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(8192), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=True, default=dt_now)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=dt_now, onupdate=dt_now
    )

    @staticmethod
    def get_all_environment(*, created_at: Optional[datetime] = None) -> List["Environment"]:
        return Environment.session.scalars(
            select(Environment).filter()).all()
