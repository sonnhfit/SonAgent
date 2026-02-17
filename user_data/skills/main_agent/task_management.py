from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel

# Lazy import to avoid circular import issues
if TYPE_CHECKING:
    from sonagent.persistence.tasks_models import Task

from sonagent.rpc import IOMsg


class TaskManagement(BaseModel):
    """
    TaskManagement - Skill for managing tasks in SonAgent
    description: Create, monitor, and manage tasks with optional cron scheduling
    
    Functions:
    - create_task: Create a new task
    - get_task_status: Get the status of a specific task
    - list_tasks: List all tasks with optional filters
    - get_pending_tasks: Get all pending tasks
    - cancel_task: Cancel a running or pending task
    - retry_task: Retry a failed task
    
    Args:
        - agent_id: The ID of the agent to assign the task to
        - content: The task description/content
        - priority: Priority level (0-10, higher is more urgent)
        - payload: Optional additional data for the task
        - scheduled_at: Optional datetime to schedule the task
        - cron_expression: Optional cron expression for recurring tasks
    """

    def _get_task_class(self):
        """Lazy load Task class to avoid circular imports"""
        from sonagent.persistence.tasks_models import Task
        return Task

    def _format_task_markdown(self, task: "Task") -> str:
        """Format a task as markdown for LLM-friendly output"""
        lines = [
            f"## Task #{task.id}",
            f"- **Agent**: {task.agent_id}",
            f"- **Status**: {task.status}",
            f"- **Priority**: {task.priority}",
            f"- **Content**: {task.content}",
        ]
        
        if task.scheduled_at:
            lines.append(f"- **Scheduled At**: {task.scheduled_at}")
        
        if task.cron_expression:
            lines.append(f"- **Cron Expression**: `{task.cron_expression}`")
        
        if task.started_at:
            lines.append(f"- **Started At**: {task.started_at}")
        
        if task.completed_at:
            lines.append(f"- **Completed At**: {task.completed_at}")
        
        if task.result:
            lines.append(f"- **Result**: {task.result}")
        
        if task.retry_count > 0:
            lines.append(f"- **Retry Count**: {task.retry_count}/{task.max_retries}")
        
        lines.append(f"- **Created At**: {task.created_at}")
        
        return "\n".join(lines)

    def create_task(
        self,
        agent_id: str,
        content: str,
        priority: int = 0,
        payload: Optional[Dict[str, Any]] = None,
        scheduled_at: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
    ) -> str:
        """
        Create a new task
        
        Args:
            agent_id: The ID of the agent to assign the task to
            content: The task description/content
            priority: Priority level (0-10, higher is more urgent)
            payload: Optional additional data for the task
            scheduled_at: Optional datetime to schedule the task
            cron_expression: Optional cron expression for recurring tasks
            
        Returns:
            Markdown-formatted string with task information
        """
        try:
            Task = self._get_task_class()
            task = Task.create_task(
                agent_id=agent_id,
                content=content,
                priority=priority,
                payload=payload,
                scheduled_at=scheduled_at,
                cron_expression=cron_expression,
            )
            
            schedule_info = ""
            if cron_expression:
                schedule_info = f" with cron schedule `{cron_expression}`"
            elif scheduled_at:
                schedule_info = f" scheduled at {scheduled_at}"
            
            message = f"## ✅ Task Created Successfully{schedule_info}\n\n"
            message += f"- **Task ID**: {task.id}\n"
            message += f"- **Agent**: {agent_id}\n"
            message += f"- **Priority**: {priority}\n"
            message += f"- **Content**: {content}\n"
            message += f"- **Status**: {task.status}\n"
            
            IOMsg.send_msg(message)
            
            return message
        except Exception as e:
            error_msg = f"## ❌ Failed to Create Task\n\nError: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg

    def get_task_status(self, task_id: int) -> str:
        """
        Get the status of a specific task
        
        Args:
            task_id: The ID of the task to check
            
        Returns:
            Markdown-formatted string with task status
        """
        try:
            Task = self._get_task_class()
            task = Task.get_task_by_id(task_id)
            
            return self._format_task_markdown(task)
        except Exception as e:
            return f"## ❌ Failed to Get Task Status\n\nError: {str(e)}"

    def list_tasks(
        self,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> str:
        """
        List all tasks with optional filters
        
        Args:
            status: Filter by task status (pending, in_progress, done, failed, cancelled)
            agent_id: Filter by agent ID
            limit: Limit the number of results
            
        Returns:
            Markdown-formatted string with list of tasks
        """
        try:
            Task = self._get_task_class()
            tasks = []
            
            if status and agent_id:
                tasks = Task.get_tasks_by_status(status)
                tasks = [t for t in tasks if t.agent_id == agent_id]
            elif status:
                tasks = Task.get_tasks_by_status(status)
            elif agent_id:
                tasks = Task.get_tasks_by_agent_id(agent_id)
            else:
                tasks = Task.get_all_tasks()
            
            if limit:
                tasks = tasks[:limit]
            
            if not tasks:
                return "## 📋 Tasks\n\nNo tasks found."
            
            filter_desc = []
            if status:
                filter_desc.append(f"status: `{status}`")
            if agent_id:
                filter_desc.append(f"agent: `{agent_id}`")
            
            filter_str = ""
            if filter_desc:
                filter_str = f" (filtered by {', '.join(filter_desc)})"
            
            message = f"## 📋 Tasks ({len(tasks)} found){filter_str}\n\n"
            
            # Group by status
            pending = [t for t in tasks if t.status == 'pending']
            in_progress = [t for t in tasks if t.status == 'in_progress']
            done = [t for t in tasks if t.status == 'done']
            failed = [t for t in tasks if t.status == 'failed']
            cancelled = [t for t in tasks if t.status == 'cancelled']
            
            if pending:
                message += f"### ⏳ Pending ({len(pending)})\n"
                for task in pending:
                    sched = f" @ {task.scheduled_at}" if task.scheduled_at else ""
                    cron = f" `{task.cron_expression}`" if task.cron_expression else ""
                    message += f"- **#{task.id}** [{task.status}] {task.content[:50]}{'...' if len(task.content) > 50 else ''} (Agent: {task.agent_id}, Priority: {task.priority}){sched}{cron}\n"
                message += "\n"
            
            if in_progress:
                message += f"### 🔄 In Progress ({len(in_progress)})\n"
                for task in in_progress:
                    message += f"- **#{task.id}** [{task.status}] {task.content[:50]}{'...' if len(task.content) > 50 else ''} (Agent: {task.agent_id})\n"
                message += "\n"
            
            if done:
                message += f"### ✅ Completed ({len(done)})\n"
                for task in done:
                    message += f"- **#{task.id}** [{task.status}] {task.content[:50]}{'...' if len(task.content) > 50 else ''}\n"
                message += "\n"
            
            if failed:
                message += f"### ❌ Failed ({len(failed)})\n"
                for task in failed:
                    message += f"- **#{task.id}** [{task.status}] {task.content[:50]}{'...' if len(task.content) > 50 else ''} (Retries: {task.retry_count}/{task.max_retries})\n"
                message += "\n"
            
            if cancelled:
                message += f"### 🚫 Cancelled ({len(cancelled)})\n"
                for task in cancelled:
                    message += f"- **#{task.id}** [{task.status}] {task.content[:50]}{'...' if len(task.content) > 50 else ''}\n"
                message += "\n"
            
            IOMsg.send_msg(message)
            
            return message
        except Exception as e:
            error_msg = f"## ❌ Failed to List Tasks\n\nError: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg

    def get_pending_tasks(self, limit: Optional[int] = None) -> str:
        """
        Get all pending tasks
        
        Args:
            limit: Limit the number of results
            
        Returns:
            Markdown-formatted string with list of pending tasks
        """
        try:
            Task = self._get_task_class()
            tasks = Task.get_pending_tasks(limit=limit)
            
            if not tasks:
                return "## ⏳ Pending Tasks\n\nNo pending tasks."
            
            message = f"## ⏳ Pending Tasks ({len(tasks)} found)\n\n"
            
            # Sort by priority (descending) then by created_at (ascending)
            sorted_tasks = sorted(tasks, key=lambda t: (-t.priority, t.created_at))
            
            for task in sorted_tasks:
                sched = f" @ {task.scheduled_at}" if task.scheduled_at else ""
                cron = f" `{task.cron_expression}`" if task.cron_expression else ""
                message += f"- **#{task.id}** | Priority: {task.priority} | Agent: {task.agent_id}\n"
                message += f"  - {task.content}\n"
                message += f"  - Created: {task.created_at}{sched}{cron}\n\n"
            
            IOMsg.send_msg(message)
            
            return message
        except Exception as e:
            error_msg = f"## ❌ Failed to Get Pending Tasks\n\nError: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg

    def cancel_task(self, task_id: int) -> str:
        """
        Cancel a pending or in-progress task
        
        Args:
            task_id: The ID of the task to cancel
            
        Returns:
            Markdown-formatted string with cancellation result
        """
        try:
            Task = self._get_task_class()
            task = Task.get_task_by_id(task_id)
            
            if task.status in ['done', 'cancelled']:
                return f"## ⚠️ Cannot Cancel Task\n\nTask #{task_id} already has status: `{task.status}`"
            
            task.cancel()
            
            message = f"## ✅ Task Cancelled\n\nTask **#{task_id}** has been cancelled successfully."
            IOMsg.send_msg(message)
            
            return message
        except Exception as e:
            error_msg = f"## ❌ Failed to Cancel Task\n\nError: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg

    def retry_task(self, task_id: int) -> str:
        """
        Retry a failed task
        
        Args:
            task_id: The ID of the task to retry
            
        Returns:
            Markdown-formatted string with retry result
        """
        try:
            Task = self._get_task_class()
            task = Task.get_task_by_id(task_id)
            
            if task.status != 'failed':
                return f"## ⚠️ Cannot Retry Task\n\nTask **#{task_id}** has status `{task.status}`. Only failed tasks can be retried."
            
            if task.retry_count >= task.max_retries:
                return f"## ⚠️ Cannot Retry Task\n\nTask **#{task_id}** has exceeded maximum retry count ({task.max_retries})."
            
            success = task.retry()
            
            if success:
                message = f"## ✅ Task Queued for Retry\n\nTask **#{task_id}** has been queued for retry (attempt {task.retry_count}/{task.max_retries})."
                IOMsg.send_msg(message)
                return message
            else:
                return f"## ❌ Failed to Retry Task\n\nTask **#{task_id}** could not be queued for retry."
        except Exception as e:
            error_msg = f"## ❌ Failed to Retry Task\n\nError: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg


# Example usage
if __name__ == "__main__":
    task_mgmt = TaskManagement()
    
    # Example: Create a simple task
    result = task_mgmt.create_task(
        agent_id="main_agent",
        content="Test task",
        priority=5,
    )
    print(result)
    
    # Example: Create a scheduled task
    # from datetime import datetime, timedelta
    # result = task_mgmt.create_task(
    #     agent_id="main_agent",
    #     content="Daily backup",
    #     priority=8,
    #     scheduled_at=datetime.now() + timedelta(days=1),
    #     cron_expression="0 2 * * *",  # Daily at 2 AM
    # )
    # print(result)
    
    # Example: List all tasks
    # result = task_mgmt.list_tasks()
    # print(result)
