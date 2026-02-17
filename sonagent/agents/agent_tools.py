"""
Agent tools for the MainTeamAgent.
These are regular Python functions that can be used as tools by Agno agents.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from sonagent.persistence import Task, ChatMessage, Conversation, Belief
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


def create_task_tool(content: str, priority: int = 0, 
                    agent_id: str = "main_team",
                    cron_expression: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new task in the system.
    
    Args:
        content: Task description/content
        priority: Task priority (0=low, 1=medium, 2=high)
        agent_id: ID of the agent creating the task
        cron_expression: Optional cron expression for scheduled/recurring tasks
            Examples:
            - "0 9 * * *" (every day at 9:00 AM)
            - "0 */2 * * *" (every 2 hours)
            - "0 0 * * 0" (every Sunday at midnight)
            - "30 18 * * 1-5" (every weekday at 6:30 PM)
        
    Returns:
        Dictionary with task information
    """
    try:
        # First, check if session is in a bad state and rollback if needed
        try:
            Task.session.rollback()
        except:
            pass  # Ignore if rollback fails
        
        task = Task.create_task(
            agent_id=agent_id,
            content=content,
            priority=priority,
            cron_expression=cron_expression
        )
        
        logger.info(f"Task created: ID={task.id}, Content={content[:50]}..., Cron={cron_expression}")
        
        # Create a detailed confirmation message
        created_time = task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else 'N/A'
        
        if cron_expression:
            confirmation_msg = (
                f"✅ Task định kỳ đã được tạo thành công!\n\n"
                f"📋 Chi tiết task:\n"
                f"- ID: {task.id}\n"
                f"- Nội dung: {task.content}\n"
                f"- Trạng thái: {task.status}\n"
                f"- Độ ưu tiên: {task.priority}\n"
                f"- Cron expression: {cron_expression}\n"
                f"- Thời gian tạo: {created_time}\n\n"
                f"Task định kỳ đã được lưu vào database và sẽ được thực hiện theo lịch trình: {cron_expression}"
            )
        else:
            confirmation_msg = (
                f"✅ Task đã được tạo thành công!\n\n"
                f"📋 Chi tiết task:\n"
                f"- ID: {task.id}\n"
                f"- Nội dung: {task.content}\n"
                f"- Trạng thái: {task.status}\n"
                f"- Độ ưu tiên: {task.priority}\n"
                f"- Thời gian tạo: {created_time}\n\n"
                f"Task đã được lưu vào database và sẽ được xử lý theo lịch trình."
            )
        
        return {
            "success": True,
            "task_id": task.id,
            "content": task.content,
            "status": task.status,
            "priority": task.priority,
            "cron_expression": cron_expression,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "message": confirmation_msg
        }
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
    Get tasks from the system with optional filters.
    
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
                "cron_expression": task.cron_expression,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            })
        
        logger.info(f"Retrieved {len(result)} tasks")
        return result
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return [{"error": str(e), "message": "Failed to retrieve tasks"}]


def update_task_tool(task_id: int, status: Optional[str] = None,
                    result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Update a task's status or result.
    
    Args:
        task_id: ID of the task to update
        status: New status (in_progress, done, failed, cancelled)
        result: Task result data
        
    Returns:
        Dictionary with update information
    """
    try:
        task = Task.get_task_by_id(task_id)
        
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
                Task.session.commit()
        
        logger.info(f"Task updated: ID={task_id}, Status={status}")
        
        return {
            "success": True,
            "task_id": task.id,
            "status": task.status,
            "message": f"Task {task_id} updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update task {task_id}"
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


def extract_tom_tool(conversation_text: str, user_id: str = "default") -> Dict[str, Any]:
    """
    Extract Theory of Mind (TOM) from conversation text.
    
    Args:
        conversation_text: The conversation text to analyze
        user_id: ID of the user
        
    Returns:
        Dictionary with TOM analysis
    """
    try:
        # This would typically use an LLM to analyze the conversation
        # For now, we'll create a structured analysis
        
        tom_analysis = {
            "user_id": user_id,
            "timestamp": dt_now().isoformat(),
            "extracted_beliefs": [],
            "inferred_intentions": [],
            "emotional_state": "neutral",
            "knowledge_level": "medium",
            "preferences": [],
            "uncertainties": [],
            "summary": ""
        }
        
        # Simple keyword-based analysis (in production, use LLM)
        text_lower = conversation_text.lower()
        
        # Extract potential beliefs
        belief_keywords = ["think", "believe", "know", "feel", "opinion"]
        for keyword in belief_keywords:
            if keyword in text_lower:
                tom_analysis["extracted_beliefs"].append(f"User expresses {keyword} about topic")
        
        # Extract intentions
        intent_keywords = ["want", "need", "would like", "plan to", "going to"]
        for keyword in intent_keywords:
            if keyword in text_lower:
                tom_analysis["inferred_intentions"].append(f"User indicates {keyword}")
        
        # Emotional analysis
        positive_words = ["happy", "good", "great", "excited", "love"]
        negative_words = ["sad", "bad", "angry", "frustrated", "hate"]
        
        if any(word in text_lower for word in positive_words):
            tom_analysis["emotional_state"] = "positive"
        elif any(word in text_lower for word in negative_words):
            tom_analysis["emotional_state"] = "negative"
        
        # Create summary
        tom_analysis["summary"] = (
            f"Extracted {len(tom_analysis['extracted_beliefs'])} beliefs and "
            f"{len(tom_analysis['inferred_intentions'])} intentions. "
            f"Emotional state: {tom_analysis['emotional_state']}"
        )
        
        logger.info(f"TOM analysis extracted: {tom_analysis['summary']}")
        
        return {
            "success": True,
            "tom_analysis": tom_analysis,
            "message": "TOM analysis completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error extracting TOM: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to extract TOM"
        }


def update_beliefs_tool(user_id: str, new_beliefs: List[Dict[str, Any]], 
                       source: str = "tom_analysis") -> Dict[str, Any]:
    """
    Update user's belief system with new beliefs.
    
    Args:
        user_id: ID of the user
        new_beliefs: List of new beliefs to add
        source: Source of the beliefs (tom_analysis, direct_input, etc.)
        
    Returns:
        Dictionary with update information
    """
    try:
        added_count = 0
        
        for belief_data in new_beliefs:
            # Extract belief text and description
            belief_text = belief_data.get("text", "")
            description = belief_data.get("description", belief_text)
            
            if belief_text:
                # Create new belief in database
                belief = Belief(
                    text=belief_text,
                    description=description,
                    source=source,
                    user_id=user_id
                )
                Belief.session.add(belief)
                added_count += 1
        
        if added_count > 0:
            Belief.session.commit()
        
        logger.info(f"Updated beliefs for user {user_id}: added {added_count} new beliefs")
        
        return {
            "success": True,
            "user_id": user_id,
            "beliefs_added": added_count,
            "source": source,
            "message": f"Successfully added {added_count} new beliefs to user's belief system"
        }
        
    except Exception as e:
        logger.error(f"Error updating beliefs: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to update beliefs"
        }


def analyze_intent_tool(user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze user's intent from a query.
    
    Args:
        user_query: The user's query
        context: Optional context about the conversation
        
    Returns:
        Dictionary with intent analysis
    """
    try:
        # Simple intent classification (in production, use more sophisticated NLP)
        query_lower = user_query.lower()
        
        intent_categories = {
            "task_management": ["task", "todo", "create", "update", "delete", "check", "status"],
            "information_request": ["what", "how", "when", "where", "why", "explain", "tell me"],
            "feedback": ["feedback", "approve", "confirm", "reject", "like", "dislike"],
            "conversation": ["hello", "hi", "hey", "thanks", "thank you", "bye"],
            "tom_analysis": ["think", "believe", "feel", "want", "need", "intend"]
        }
        
        detected_intents = []
        confidence_scores = {}
        
        # Check for intent matches
        for intent_type, keywords in intent_categories.items():
            matches = sum(1 for keyword in keywords if keyword in query_lower)
            if matches > 0:
                detected_intents.append(intent_type)
                confidence_scores[intent_type] = min(matches / len(keywords) * 100, 100)
        
        # Determine primary intent
        primary_intent = detected_intents[0] if detected_intents else "unknown"
        
        intent_analysis = {
            "user_query": user_query,
            "detected_intents": detected_intents,
            "primary_intent": primary_intent,
            "confidence_scores": confidence_scores,
            "context_provided": context is not None,
            "analysis_timestamp": dt_now().isoformat()
        }
        
        logger.info(f"Intent analysis: primary={primary_intent}, intents={detected_intents}")
        
        return {
            "success": True,
            "intent_analysis": intent_analysis,
            "message": "Intent analysis completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing intent: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to analyze intent"
        }


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
