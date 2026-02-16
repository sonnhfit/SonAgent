import logging
from typing import Annotated, Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from sonagent.persistence.tasks_models import Task
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
    if body is None:
        return JSONResponse(content={"error": "Request body is required"}, status_code=400)
    
    # Create task using the new Task model
    task = Task.create_task(
        agent_id=body.agent_id if body.agent_id else "default",
        content=body.input,
        priority=body.priority if body.priority else 0,
        payload=body.additional_input if body.additional_input else None
    )
    
    # trigger task handler

    return JSONResponse(content={"task_id": task.id, "status": "created"}, status_code=200)


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
    try:
        task_id_int = int(task_id)
        return Task.get_task_by_id(task_id_int)
    except ValueError:
        return JSONResponse(content={"error": "Task ID must be an integer"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=404)


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
    Note: The new Task model doesn't have steps field like the old one.
    This endpoint returns empty steps for now.
    """
    try:
        task_id_int = int(task_id)
        task = Task.get_task_by_id(task_id_int)
        # Return empty steps since the new model doesn't have steps
        return TaskStepsListResponse(
            steps=[],
            pagination=Pagination(
                total_items=0,
                total_pages=0,
                current_page=current_page,
                page_size=page_size,
            ),
        )
    except ValueError:
        return JSONResponse(content={"error": "Task ID must be an integer"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=404)


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
    """
    Get a specific step for a task.
    Note: The new Task model doesn't have steps, so this returns empty.
    """
    return JSONResponse(content={"message": "Steps not implemented in new Task model"}, status_code=501)


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
