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


def add_target_tool(target: str, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a new target (objective) to the system.
    
    Args:
        target: The target description (short)
        description: Detailed description (optional)
        
    Returns:
        Dictionary with success status and created target info
    """
    try:
        # Validate inputs
        if not target or not target.strip():
            return {
                "success": False,
                "error": "Target cannot be empty",
                "message": "Failed to add target: target is required"
            }
        
        # Create target
        target_obj = Target.create_target(
            target=target.strip(),
            description=description.strip() if description else ""
        )
        
        logger.info(f"Added target {target_obj.id}: {target}")
        
        return {
            "success": True,
            "target_id": target_obj.id,
            "target": target_obj.target,
            "description": target_obj.description,
            "message": f"Target '{target}' added successfully"
        }
        
    except Exception as e:
        logger.error(f"Error adding target: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to add target"
        }


def delete_target_tool(target_id: int) -> Dict[str, Any]:
    """
    Delete a target by ID.
    
    Args:
        target_id: ID of the target to delete
        
    Returns:
        Dictionary with success status
    """
    try:
        # Check if target exists
        target = Target.get_target_by_id(target_id)
        
        # Delete target
        deleted = Target.delete_target(target_id)
        
        if deleted:
            logger.info(f"Deleted target {target_id}: {target.target}")
            return {
                "success": True,
                "target_id": target_id,
                "message": f"Target {target_id} deleted successfully"
            }
        else:
            return {
                "success": False,
                "error": "Target not found",
                "message": f"Target {target_id} not found"
            }
        
    except Exception as e:
        logger.error(f"Error deleting target: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete target {target_id}"
        }


def update_target_tool(target_id: int, target: Optional[str] = None, 
                      description: Optional[str] = None) -> Dict[str, Any]:
    """
    Update an existing target.
    
    Args:
        target_id: ID of the target to update
        target: New target description (optional)
        description: New detailed description (optional)
        
    Returns:
        Dictionary with success status and updated target info
    """
    try:
        # Get the target
        target_obj = Target.get_target_by_id(target_id)
        
        # Prepare update fields
        update_fields = {}
        if target is not None:
            if not target.strip():
                return {
                    "success": False,
                    "error": "Target cannot be empty",
                    "message": "Failed to update target: target cannot be empty"
                }
            update_fields["target"] = target.strip()
        
        if description is not None:
            update_fields["description"] = description.strip() if description else ""
        
        # Update target
        target_obj.update(**update_fields)
        
        logger.info(f"Updated target {target_id}: fields={list(update_fields.keys())}")
        
        return {
            "success": True,
            "target_id": target_id,
            "updated_fields": list(update_fields.keys()),
            "message": f"Target {target_id} updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating target: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update target {target_id}"
        }


def send_rpc_message_tool(
    message: str,
) -> Dict[str, Any]:
    """
    Send a message via RPC to notify users (e.g., through Telegram, API, etc.).
    
    Args:
        message: The message content to send
        
    Returns:
        Dictionary with success status and message info
    """
    try:
        # Import here to avoid circular imports
        from sonagent.enums.rpcmessagetype import RPCMessageType
        from sonagent.rpc.io import IOMsg
        message_type = "chat"
        # Validate message type
        valid_types = {
            "status": RPCMessageType.STATUS,
            "chat": RPCMessageType.CHAT,
            "warning": RPCMessageType.WARNING,
            "startup": RPCMessageType.STARTUP,
            "exception": RPCMessageType.EXCEPTION
        }
        
        if message_type.lower() not in valid_types:
            return {
                "success": False,
                "error": f"Invalid message type. Must be one of: {', '.join(valid_types.keys())}",
                "message": f"Failed to send RPC message: invalid type '{message_type}'"
            }
        
        # Get the RPC type
        rpc_type = valid_types[message_type.lower()]
        
        # Check if RPC is available
        if not IOMsg.rpc:
            logger.warning("RPC not initialized, message will be printed locally")
            print(f"[RPC {message_type.upper()}] {message}")
            return {
                "success": True,
                "message_sent": False,
                "rpc_available": False,
                "local_print": True,
                "message": f"RPC not initialized, message printed locally: {message[:50]}..."
            }
        
        # Send the message via RPC
        IOMsg.rpc.send_msg({
            'type': rpc_type,
            'status': message if message_type.lower() == "status" else None,
            'message': message if message_type.lower() == "chat" else None
        })
        
        logger.info(f"Sent RPC message via {message_type}: {message[:100]}...")
        
        return {
            "success": True,
            "message_sent": True,
            "message_type": message_type,
            "message_preview": message[:100] + ("..." if len(message) > 100 else ""),
            "message": f"RPC message sent successfully via {message_type}"
        }
        
    except Exception as e:
        logger.error(f"Error sending RPC message: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to send RPC message: {str(e)}"
        }