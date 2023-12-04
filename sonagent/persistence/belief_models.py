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


logger = logging.getLogger(__name__)


class Belief(ModelBase):
    __tablename__ = "belief"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
