"""
Worker Agent Tools for task prioritization and execution.
These tools are used by the WorkerTeamAgent for managing tasks and targets.
"""
import logging
from typing import Any, Dict, List, Optional
import time

from agno.tools import tool
from sonagent.persistence import Task, Target
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)



def get_task_list_tool(status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get list of tasks with optional filtering.

    Args:
        status: Filter by task status (pending, in_progress, done, failed, cancelled)
        limit: Maximum number of tasks to return

    Returns:
        List of task dictionaries with execution data
    """
    try:
        if status:
            tasks = Task.get_tasks_by_status(status)
        else:
            tasks = Task.get_all_tasks()

        # Apply limit
        tasks = tasks[:limit]

        result = []
        for task in tasks:
            task_dict = {
                "id": task.id,
                "content": task.content,
                "status": task.status,
                "execution_count": task.execution_count,
                "challenge": task.challenge,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
            result.append(task_dict)

        logger.info(f"Retrieved {len(result)} tasks")
        return result

    except Exception as e:
        logger.error(f"Error getting task list: {e}")
        return [{"error": str(e), "message": "Failed to retrieve tasks"}]



def get_targets_tool(status: Optional[str] = "active") -> List[Dict[str, Any]]:
    """
    Get list of targets (objectives) with their progress.

    Args:
        status: Filter by target status (active, completed)

    Returns:
        List of target dictionaries
    """
    try:
        if status == "active":
            targets = Target.get_active_targets()
        else:
            targets = Target.get_all_targets()

        result = []
        for target in targets:
            target_dict = {
                "id": target.id,
                "target": target.target,
                "description": target.description,
            }
            result.append(target_dict)

        logger.info(f"Retrieved {len(result)} targets")
        return result

    except Exception as e:
        logger.error(f"Error getting targets: {e}")
        return [{"error": str(e), "message": "Failed to retrieve targets"}]


def update_task_execution_data_tool(
    task_id: int,
    summary: Optional[str] = None,
    challenge: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update task execution data including summary, challenge level, and status.
    
    Args:
        task_id: ID of the task to update
        summary: Summary text to store in execution_data field (max 10000 chars)
        challenge: Challenge of task 
        status: Task status (pending, in_progress, done, failed, cancelled)
        
    Returns:
        Dictionary with success status and updated task info
    """
    try:
        # Validate challenge if provided
        
        # Validate status if provided
        valid_statuses = {"pending", "in_progress", "done", "failed", "cancelled"}
        if status and status.lower() not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid status value. Must be one of: {', '.join(valid_statuses)}"
            }
        
        # Get the task
        task = Task.get_task_by_id(task_id)
        
        # Update fields if provided
        if summary is not None:
            # Truncate if too long
            if len(summary) > 10000:
                summary = summary[:9997] + "..."
            task.execution_data = summary
        
        if challenge is not None:
            task.challenge = challenge.lower()
        
        if status is not None:
            task.status = status.lower()
            # Update timestamps based on status changes
            if status.lower() == "in_progress" and not task.started_at:
                task.started_at = dt_now()
            elif status.lower() in ["done", "failed", "cancelled"] and not task.completed_at:
                task.completed_at = dt_now()
        
        # Commit changes
        Task.session.commit()
        
        logger.info(f"Updated task {task_id}: summary={summary is not None}, "
                   f"challenge={challenge}, status={status}")
        
        return {
            "success": True,
            "task_id": task_id,
            "updated_fields": {
                "summary_updated": summary is not None,
                "challenge_updated": challenge is not None,
                "status_updated": status is not None
            },
            "message": f"Task {task_id} updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating task execution data: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update task {task_id}"
        }

