import logging
from typing import ClassVar, List, Optional

from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from sonagent.persistence.base import ModelBase, SessionType
from sonagent.utils.datetime_helpers import dt_now

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


class Artifact(ModelBase):
    __tablename__ = "artifact"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_created: Mapped[bool] = mapped_column(nullable=False, default=False)
    relative_path: Mapped[str] = mapped_column(String, nullable=True)

    @staticmethod
    def get_all_artifacts() -> List["Artifact"]:
        return Artifact.session.scalars(select(Artifact)).all()
    
    @staticmethod
    def get_artifact_by_id(artifact_id: str) -> "Artifact":
        return Artifact.session.scalars(
            select(Artifact).filter(Artifact.artifact_id == artifact_id)).one()
    
    @staticmethod
    def get_artifacts_by_ids(artifact_ids: List[str]) -> List["Artifact"]:
        return Artifact.session.scalars(
            select(Artifact).filter(Artifact.artifact_id.in_(artifact_ids))).all()
    
    @staticmethod
    def get_artifacts_by_relative_path(relative_path: str) -> List["Artifact"]:
        return Artifact.session.scalars(
            select(Artifact).filter(Artifact.relative_path == relative_path)).all()


class Step(ModelBase):
    __tablename__ = "step"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    step_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=True)
    output: Mapped[str] = mapped_column(String, nullable=True)
    additional_output: Mapped[str] = mapped_column(String, nullable=True)
    artifacts: Mapped[List[str]] = mapped_column(String, nullable=True)
    is_last: Mapped[bool] = mapped_column(nullable=False, default=False)
    additional_properties: Mapped[str] = mapped_column(String, nullable=True)

    @staticmethod
    def get_all_steps() -> List["Step"]:
        return Step.session.scalars(select(Step)).all()
    
    @staticmethod
    def get_step_by_id(task_id: str, step_id: str) -> "Step":
        return Step.session.scalars(
            select(Step).filter(Step.task_id == task_id, Step.step_id == step_id)).one()
    
    @staticmethod
    def get_steps_by_task_id(task_id: str) -> List["Step"]:
        return Step.session.scalars(
            select(Step).filter(Step.task_id == task_id)).all()
    
    @staticmethod
    def get_step_by_task_id(task_id: str, step_id: str) -> "Step":
        return Step.session.scalars(
            select(Step).filter(
                Step.task_id == task_id, Step.step_id == step_id)).one()


class Task(ModelBase):
    __tablename__ = "task"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    artifacts: Mapped[List[Artifact]] = mapped_column(String, nullable=True)
    steps: Mapped[List[str]] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=True, default=dt_now)

    @staticmethod
    def get_all_tasks() -> List["Task"]:
        return Task.session.scalars(select(Task)).all()
    
    @staticmethod
    def get_task_by_id(task_id: str) -> "Task":
        return Task.session.scalars(
            select(Task).filter(Task.task_id == task_id)).one()

