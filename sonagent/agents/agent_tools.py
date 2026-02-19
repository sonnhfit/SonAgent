"""
Agent tools for the MainTeamAgent.
These are regular Python functions that can be used as tools by Agno agents.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from sonagent.persistence import Task, ChatMessage, Conversation
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


def create_task_tool(content: str, priority: int = 0, 
                    agent_id: str = "main_team",
                    cron_expression: Optional[str] = None,
                    scheduled_at: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new task in the system.
    
    Args:
        content: Task description/content (required)
        priority: Task priority (0=low, 1=medium, 2=high)
        agent_id: ID of the agent creating the task
        cron_expression: Optional cron expression for scheduled/recurring tasks
            Examples:
            - "0 9 * * *" (every day at 9:00 AM)
            - "0 */2 * * *" (every 2 hours)
            - "0 0 * * 0" (every Sunday at midnight)
            - "30 18 * * 1-5" (every weekday at 6:30 PM)
        scheduled_at: Optional scheduled datetime for the task (string)
        
    Returns:
        Dictionary with task information
    """
    try:
        # Handle scheduled_at parameter - it might be an empty dict or invalid value
        actual_scheduled_at = None
        if scheduled_at is not None:
            if isinstance(scheduled_at, dict):
                # If it's an empty dict, treat it as None
                if scheduled_at:
                    # Try to parse dict to datetime if it has datetime fields
                    # This is a fallback for when LLM passes a dict representation
                    try:
                        from datetime import datetime as dt
                        # Check if it has common datetime fields
                        if 'year' in scheduled_at and 'month' in scheduled_at and 'day' in scheduled_at:
                            actual_scheduled_at = dt(
                                scheduled_at['year'],
                                scheduled_at['month'],
                                scheduled_at['day'],
                                scheduled_at.get('hour', 0),
                                scheduled_at.get('minute', 0),
                                scheduled_at.get('second', 0),
                                scheduled_at.get('microsecond', 0)
                            )
                    except:
                        pass  # If parsing fails, keep as None
                # If empty dict or parsing failed, treat as None
            elif isinstance(scheduled_at, datetime):
                actual_scheduled_at = scheduled_at
            elif isinstance(scheduled_at, str):
                # Try to parse string to datetime
                try:
                    from datetime import datetime as dt
                    # First try fromisoformat for ISO 8601 format (including with microseconds)
                    try:
                        actual_scheduled_at = dt.fromisoformat(scheduled_at)
                    except ValueError:
                        # If fromisoformat fails, try common formats
                        formats = [
                            '%Y-%m-%d %H:%M:%S.%f',  # With microseconds
                            '%Y-%m-%d %H:%M:%S',     # Without microseconds
                            '%Y-%m-%dT%H:%M:%S.%f',  # ISO with microseconds
                            '%Y-%m-%dT%H:%M:%S',     # ISO without microseconds
                            '%Y-%m-%d',              # Date only
                            '%d/%m/%Y %H:%M',        # European format with time
                            '%d/%m/%Y',              # European date only
                            '%Y-%m-%d %H:%M:%S.%f%z', # With microseconds and timezone
                            '%Y-%m-%dT%H:%M:%S.%f%z', # ISO with microseconds and timezone
                            '%Y-%m-%d %H:%M:%S%z',   # Without microseconds with timezone
                            '%Y-%m-%dT%H:%M:%S%z',   # ISO without microseconds with timezone
                        ]
                        for fmt in formats:
                            try:
                                actual_scheduled_at = dt.strptime(scheduled_at, fmt)
                                break
                            except:
                                continue
                except:
                    pass  # If parsing fails, keep as None
        
        # First, check if session is in a bad state and rollback if needed
        try:
            Task.session.rollback()
        except:
            pass  # Ignore if rollback fails
        
        task = Task.create_task(
            agent_id=agent_id,
            content=content,
            priority=priority,
            cron_expression=cron_expression,
            scheduled_at=actual_scheduled_at
        )
        Task.session.commit()
        
        logger.info(f"Task created: ID={task.id}, Content={content[:50]}..., Cron={cron_expression}, Scheduled_at={actual_scheduled_at}::{scheduled_at}")
        
        # Create a detailed confirmation message
        created_time = task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else 'N/A'
        scheduled_time = actual_scheduled_at.strftime('%Y-%m-%d %H:%M:%S') if actual_scheduled_at else None
        
        if cron_expression:
            confirmation_msg = (
                f"✅ Task định kỳ đã được tạo thành công!\n\n"
                f"📋 Chi tiết task:\n"
                f"- ID: {task.id}\n"
                f"- Nội dung: {task.content}\n"
                f"- Trạng thái: {task.status}\n"
                f"- Độ ưu tiên: {task.priority}\n"
                f"- Cron expression: {cron_expression}\n"
                f"- Thời gian tạo: {created_time}\n"
            )
            if scheduled_time:
                confirmation_msg += f"- Thời gian lên lịch: {scheduled_time}\n"
            confirmation_msg += f"\nTask định kỳ đã được lưu vào database và sẽ được thực hiện theo lịch trình: {cron_expression}"
        else:
            confirmation_msg = (
                f"✅ Task đã được tạo thành công!\n\n"
                f"📋 Chi tiết task:\n"
                f"- ID: {task.id}\n"
                f"- Nội dung: {task.content}\n"
                f"- Trạng thái: {task.status}\n"
                f"- Độ ưu tiên: {task.priority}\n"
                f"- Thời gian tạo: {created_time}\n"
            )
            if scheduled_time:
                confirmation_msg += f"- Thời gian lên lịch: {scheduled_time}\n"
            confirmation_msg += f"\nTask đã được lưu vào database và sẽ được xử lý theo lịch trình."
        
        result = {
            "success": True,
            "task_id": task.id,
            "content": task.content,
            "status": task.status,
            "priority": task.priority,
            "cron_expression": cron_expression,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "message": confirmation_msg
        }
        if actual_scheduled_at:
            result["scheduled_at"] = actual_scheduled_at.isoformat()
        return result
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        # Try to rollback the session to clean up
        try:
            Task.session.rollback()
        except:
            pass
        
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create task"
        }


def get_tasks_tool(status: Optional[str] = None, 
                  agent_id: Optional[str] = None,
                  limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get tasks from the system with optional filters, or get all tasks.
    
    Args:
        status: Filter by task status (pending, in_progress, done, failed, cancelled)
        agent_id: Filter by agent ID
        limit: Maximum number of tasks to return
        
    Returns:
        List of task dictionaries
    """
    try:
        tasks = []
        
        if status:
            tasks = Task.get_tasks_by_status(status)
        elif agent_id:
            tasks = Task.get_tasks_by_agent_id(agent_id)
        else:
            tasks = Task.get_all_tasks()
        
        # Apply limit
        tasks = tasks[:limit]
        
        result = []
        for task in tasks:
            result.append({
                "id": task.id,
                "agent_id": task.agent_id,
                "content": task.content,
                "status": task.status,
                "priority": task.priority,
                "payload": task.payload,
                "result": task.result,
                "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
                "cron_expression": task.cron_expression,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "execution_count": task.execution_count,
                "total_tokens_used": task.total_tokens_used,
                "challenge": task.challenge,
                "execution_data": task.execution_data,
                "last_execution_tokens": task.last_execution_tokens,
                "last_execution_duration": task.last_execution_duration,
                "success_rate": task.success_rate,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            })
        
        logger.info(f"Retrieved {len(result)} tasks")
        return result
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return [{"error": str(e), "message": "Failed to retrieve tasks"}]


def update_task_tool(task_id: int, 
                    content: Optional[str] = None,
                    status: Optional[str] = None,
                    priority: Optional[int] = None,
                    cron_expression: Optional[str] = None,
                    scheduled_at: Optional[datetime] = None,
                    started_at: Optional[datetime] = None,
                    result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Update a task's fields.
    
    Args:
        task_id: ID of the task to update
        content: New task content/description
        status: New status (pending, in_progress, done, failed, cancelled)
        priority: New priority (0=low, 1=medium, 2=high)
        cron_expression: New cron expression for scheduled tasks
        scheduled_at: New scheduled datetime for the task (datetime object)
        started_at: New start time (datetime object)
        result: Task result data
        
    Returns:
        Dictionary with update information
    """
    try:
        task = Task.get_task_by_id(task_id)
        
        # Update content if provided
        if content is not None:
            task.content = content
        
        # Update priority if provided
        if priority is not None:
            task.priority = priority
        
        # Update cron expression if provided
        if cron_expression is not None:
            task.cron_expression = cron_expression
        
        # Update scheduled_at if provided
        if scheduled_at is not None:
            task.scheduled_at = scheduled_at
        
        # Update started_at if provided
        if started_at is not None:
            task.started_at = started_at
        
        # Update status if provided (with special handling for status transitions)
        if status:
            if status == "in_progress":
                task.start()
            elif status == "done":
                task.complete(result)
            elif status == "failed":
                task.fail(result.get("error") if result else None)
            elif status == "cancelled":
                task.cancel()
            else:
                task.status = status
        
        # Update result if provided (and not already set by status methods)
        if result is not None and task.result != result:
            task.result = result
        
        # Commit all changes
        Task.session.commit()
        
        logger.info(f"Task updated: ID={task_id}, Content updated={content is not None}, "
                   f"Status={status}, Priority={priority}, Cron={cron_expression is not None}, Scheduled_at={scheduled_at is not None}")
        
        # Build response message
        updates = []
        if content is not None:
            updates.append("content")
        if status is not None:
            updates.append("status")
        if priority is not None:
            updates.append("priority")
        if cron_expression is not None:
            updates.append("cron_expression")
        if scheduled_at is not None:
            updates.append("scheduled_at")
        if started_at is not None:
            updates.append("started_at")
        if result is not None:
            updates.append("result")
        
        update_message = f"Updated fields: {', '.join(updates)}" if updates else "No fields updated"
        
        return {
            "success": True,
            "task_id": task.id,
            "content": task.content,
            "status": task.status,
            "priority": task.priority,
            "cron_expression": task.cron_expression,
            "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "result": task.result,
            "message": f"Task {task_id} updated successfully. {update_message}"
        }
    except Exception as e:
        logger.error(f"Error updating task: {e}", exc_info=True)
        # Try to rollback the session to clean up
        try:
            Task.session.rollback()
        except:
            pass
        
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update task {task_id}"
        }


def delete_task_tool(task_id: int) -> Dict[str, Any]:
    """
    Delete a task from the system.
    
    Args:
        task_id: ID of the task to delete
        
    Returns:
        Dictionary with deletion information
    """
    try:
        task = Task.get_task_by_id(task_id)
        
        # Store task info before deletion for response
        task_info = {
            "id": task.id,
            "content": task.content,
            "status": task.status,
            "priority": task.priority
        }
        
        # Delete the task
        Task.session.delete(task)
        Task.session.commit()
        
        logger.info(f"Task deleted: ID={task_id}, Content={task_info['content'][:50]}...")
        
        return {
            "success": True,
            "deleted_task": task_info,
            "message": f"Task {task_id} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting task: {e}", exc_info=True)
        # Try to rollback the session to clean up
        try:
            Task.session.rollback()
        except:
            pass
        
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete task {task_id}"
        }


def save_chat_message_tool(conversation_id: str, role: str, 
                          content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Save a chat message to persistent storage.
    
    Args:
        conversation_id: Unique conversation identifier
        role: Message role (user, assistant, system)
        content: Message content
        metadata: Additional metadata
        
    Returns:
        Dictionary with save information
    """
    try:
        message = ChatMessage.create_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata
        )
        
        # Also update conversation metadata
        Conversation.create_or_update(
            conversation_id=conversation_id,
            title=metadata.get("title") if metadata else None,
            metadata=metadata
        )
        
        logger.debug(f"Chat message saved: Conversation={conversation_id}, Role={role}")
        
        return {
            "success": True,
            "message_id": message.id,
            "conversation_id": message.conversation_id,
            "role": message.role,
            "created_at": message.created_at.isoformat() if message.created_at else None,
            "message": "Chat message saved successfully"
        }
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to save chat message"
        }


def get_chat_history_tool(conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get chat history for a conversation.
    
    Args:
        conversation_id: Conversation identifier
        limit: Maximum number of messages to return
        
    Returns:
        List of chat message dictionaries
    """
    try:
        messages = ChatMessage.get_conversation_messages(
            conversation_id=conversation_id,
            limit=limit
        )
        
        result = []
        for message in messages:
            result.append(message.to_dict())
        
        logger.debug(f"Retrieved {len(result)} messages for conversation {conversation_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return [{"error": str(e), "message": "Failed to retrieve chat history"}]

def request_feedback_tool(action: str, context: str, 
                         feedback: Optional[str] = None) -> Dict[str, Any]:
    """
    Request human feedback for an agent action.
    
    Args:
        action: The action requiring feedback
        context: Context about why feedback is needed
        feedback: User feedback (collected via user input)
        
    Returns:
        Dictionary with feedback information
    """
    try:
        # If feedback is provided, process it
        if feedback:
            # Save feedback to database or process it
            logger.info(f"Feedback received for action '{action}': {feedback}")
            
            return {
                "success": True,
                "action": action,
                "feedback": feedback,
                "processed": True,
                "message": "Feedback processed successfully"
            }
        else:
            # Request feedback (tool will pause for user input)
            return {
                "success": True,
                "action": action,
                "context": context,
                "needs_feedback": True,
                "message": "Feedback requested for action"
            }
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to process feedback"
        }


def process_feedback_tool(action: str, feedback: str, 
                         learning_note: Optional[str] = None) -> Dict[str, Any]:
    """
    Process and incorporate user feedback into agent learning.
    
    Args:
        action: The action that received feedback
        feedback: User feedback text
        learning_note: Optional note about what was learned
        
    Returns:
        Dictionary with processing information
    """
    try:
        # Here you would implement feedback processing logic
        # For now, we'll just log it
        logger.info(f"Processing feedback for action '{action}': {feedback}")
        
        if learning_note:
            logger.info(f"Learning note: {learning_note}")
        
        # In a real implementation, you might:
        # 1. Store feedback in a database
        # 2. Update agent behavior based on feedback
        # 3. Trigger retraining or adjustment
        
        return {
            "success": True,
            "action": action,
            "feedback_processed": True,
            "learning_note": learning_note or "Feedback recorded for future improvement",
            "message": "Feedback processed and incorporated into learning"
        }
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to process feedback"
        }


def coordinate_agents_tool(request: str, 
                          agent_types: List[str] = None) -> Dict[str, Any]:
    """
    Coordinate multiple agents to handle a complex request.
    
    Args:
        request: The user request to handle
        agent_types: Types of agents to involve (task, tom, feedback, assistant)
        
    Returns:
        Dictionary with coordination results
    """
    try:
        # This is a placeholder implementation
        # In a real implementation, this would actually coordinate agents
        
        coordination_result = {
            "request": request,
            "agents_involved": agent_types or ["assistant"],
            "results": {},
            "summary": f"Request '{request[:50]}...' will be handled by: {', '.join(agent_types) if agent_types else 'assistant'}"
        }
        
        logger.info(f"Coordinating agents for request: {agent_types}")
        
        return coordination_result
        
    except Exception as e:
        logger.error(f"Error coordinating agents: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to coordinate agents"
        }


def respond_to_user_tool(response: str, 
                        conversation_id: str,
                        save_to_history: bool = True) -> Dict[str, Any]:
    """
    Send a response to the user and optionally save to chat history.
    
    Args:
        response: The response to send to user
        conversation_id: Conversation identifier
        save_to_history: Whether to save the response to chat history
        
    Returns:
        Dictionary with response information
    """
    try:
        # Save assistant response to chat history if requested
        if save_to_history:
            save_chat_message_tool(
                conversation_id=conversation_id,
                role="assistant",
                content=response,
                metadata={"tool": "respond_to_user_tool"}
            )
        
        logger.debug(f"Response prepared for conversation {conversation_id}")
        
        return {
            "success": True,
            "response": response,
            "conversation_id": conversation_id,
            "saved_to_history": save_to_history,
            "message": "Response prepared successfully"
        }
    except Exception as e:
        logger.error(f"Error preparing response: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to prepare response"
        }
