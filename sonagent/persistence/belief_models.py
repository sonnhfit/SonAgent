import logging
from sonagent.persistence.base import ModelBase, SessionType
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
    name: Mapped[str] = mapped_column(String, nullable=False)
    metadata: Mapped[str] = mapped_column(String, nullable=False)
    create_date: Mapped[datetime] = mapped_column(nullable=True, default=dt_now)

    def apply_sync(self, *args, **kwargs):
        """
        Load the belief to the agent memory.
        make sure data in db is synced with memory
        """
        pass


