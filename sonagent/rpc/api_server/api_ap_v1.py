import logging
from typing import Annotated, Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from sonagent.persistence.planning_models import Step, Task
from sonagent.rpc.api_server.ap_models import (Pagination, StepRequestBody,
                                               TaskListResponse,
                                               TaskRequestBody,
                                               TaskStepsListResponse)

logger = logging.getLogger(__name__)


# Public API, requires no auth.
router_public = APIRouter()
# Private API, protected by authentication
router = APIRouter()


@router_public.post("/agent/tasks", tags=["agent"])
def create_agent_task(body: TaskRequestBody | None = None):
    """
    Create a new task.
    """
    task = Task()
    task.save()

    # trigger task handler

    return JSONResponse(content=[], status_code=200)


@router_public.get("/agent/tasks")
async def list_agent_tasks_ids(page_size: int = 10, current_page: int = 1):
    tasks = Task.get_all_tasks()
    start_index = (current_page - 1) * page_size
    end_index = start_index + page_size
    return TaskListResponse(
        tasks=tasks[start_index:end_index],
        pagination=Pagination(
            total_items=len(tasks),
            total_pages=len(tasks) // page_size,
            current_page=current_page,
            page_size=page_size,
        ),
    )


@router_public.get("/agent/tasks/{task_id}", tags=["agent"])
async def get_agent_task(task_id: str):
    """
    Get details about a specified agent task.
    """
    return Task.get_task_by_id(task_id)


@router_public.get(
    "/agent/tasks/{task_id}/steps",
    response_model=TaskStepsListResponse,
    tags=["agent"],
)
async def list_agent_task_steps(
    task_id: str, page_size: int = 10, current_page: int = 1
):
    """
    List all steps for the specified task.
    """
    task = Task.get_task_by_id(task_id)
    start_index = (current_page - 1) * page_size
    end_index = start_index + page_size
    return TaskStepsListResponse(
        steps=task.steps[start_index:end_index],
        pagination=Pagination(
            total_items=len(task.steps),
            total_pages=len(task.steps) // page_size,
            current_page=current_page,
            page_size=page_size,
        ),
    )


@router_public.post(
    "/agent/tasks/{task_id}/steps",
    tags=["agent"]
)
async def execute_agent_task_step(
    task_id: str,
    body: StepRequestBody | None = None,
):
    return {}


@router_public.get(
    "/agent/tasks/{task_id}/steps/{step_id}",
    tags=["agent"],
)
async def get_agent_task_step(task_id: str, step_id: str):
    return Step.get_step_by_task_id(task_id=task_id, step_id=step_id)


@router_public.get(
    "/agent/tasks/{task_id}/artifacts",
    tags=["agent"]
)
async def list_agent_task_artifacts(task_id: str):
    """
    List all artifacts for the specified task.
    """
    return {}


@router_public.post(
    "/agent/tasks/{task_id}/artifacts",
    tags=["agent"],
)
async def upload_agent_task_artifacts(
    task_id: str,
    file: Annotated[UploadFile, File()],
    relative_path: Annotated[Optional[str], Form()] = None,
):
    """
    Upload an artifact for the specified task.
    """
    return {}


@router_public.get(
    "/agent/tasks/{task_id}/artifacts/{artifact_id}",
    tags=["agent"],
)
async def download_agent_task_artifacts(task_id: str, artifact_id: str) -> FileResponse:
    """
    Download the specified artifact.
    """
    artifact = object
    path = ""
    return FileResponse(
        path=path, media_type="application/octet-stream",
        filename=artifact.file_name
    )
