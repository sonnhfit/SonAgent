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


class SkillDocs(ModelBase):
    __tablename__ = "skill_docs"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_name: Mapped[str] = mapped_column(String, nullable=False)
    docs: Mapped[str] = mapped_column(String, nullable=True)
    keywords: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=True, default=dt_now)

    @staticmethod
    def get_all_plans(*, created_at: Optional[str] = None) -> List["SkillDocs"]:
        return SkillDocs.session.scalars(
            select(SkillDocs).filter()).all()
    
    @staticmethod
    def get_plan_by_id(id: int) -> "SkillDocs":
        return SkillDocs.session.scalars(
            select(SkillDocs).filter(SkillDocs.id == id)).one()
    
    @staticmethod
    def get_plan_by_ids(ids: List[int]) -> List["SkillDocs"]:
        return SkillDocs.session.scalars(
            select(SkillDocs).filter(SkillDocs.id.in_(ids)).order_by(SkillDocs.created_at.asc())).all()
