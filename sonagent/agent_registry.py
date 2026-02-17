"""
Agent Registry - Central registry for all agents in the system.
Manages agent registration, communication, and status tracking.
"""
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for managing agents and inter-agent communication.
    
    Features:
    - Register/unregister agents
    - Track agent status
    - Enable communication between agents
    - Store agent messages/updates
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self.agents = {}  # agent_id -> agent info
        self.messages = []  # Communication messages between agents
        self.status_updates = {}  # agent_id -> list of status updates
        self._lock = threading.Lock()
        
        logger.info("Agent Registry initialized")
    
    def register_agent(self, agent: Any) -> None:
        """
        Register an agent in the registry.
        
        Args:
            agent: Agent instance to register
        """
        with self._lock:
            agent_id = agent.agent_id
            self.agents[agent_id] = {
                'agent': agent,
                'agent_id': agent_id,
                'agent_name': agent.agent_name,
                'status': agent.status,
                'registered_at': dt_now(),
                'last_update': dt_now()
            }
            self.status_updates[agent_id] = []
            
            logger.info(f"Registered agent: {agent_id} ({agent.agent_name})")
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: ID of agent to unregister
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                if agent_id in self.status_updates:
                    del self.status_updates[agent_id]
                logger.info(f"Unregistered agent: {agent_id}")
                return True
            return False
    
    def update_agent_status(
        self,
        agent_id: str,
        status: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update agent status.
        
        Args:
            agent_id: Agent ID
            status: New status string
            data: Optional additional data
        """
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id]['status'] = status
                self.agents[agent_id]['last_update'] = dt_now()
                
                # Store status update history
                update_entry = {
                    'timestamp': dt_now(),
                    'status': status,
                    'data': data or {}
                }
                self.status_updates[agent_id].append(update_entry)
                
                # Keep only last 100 status updates per agent
                if len(self.status_updates[agent_id]) > 100:
                    self.status_updates[agent_id] = self.status_updates[agent_id][-100:]
                
                logger.debug(f"Updated status for agent {agent_id}: {status}")
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent status dict or None if not found
        """
        with self._lock:
            if agent_id in self.agents:
                return {
                    'agent_id': agent_id,
                    'agent_name': self.agents[agent_id]['agent_name'],
                    'status': self.agents[agent_id]['status'],
                    'last_update': self.agents[agent_id]['last_update'].isoformat()
                }
            return None
    
    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered agents.
        
        Returns:
            Dictionary of agent_id -> agent info
        """
        with self._lock:
            result = {}
            for agent_id, agent_info in self.agents.items():
                result[agent_id] = {
                    'agent_id': agent_id,
                    'agent_name': agent_info['agent_name'],
                    'status': agent_info['status'],
                    'registered_at': agent_info['registered_at'].isoformat(),
                    'last_update': agent_info['last_update'].isoformat()
                }
            return result
    
    def send_message(
        self,
        from_agent_id: str,
        to_agent_id: str,
        message: Any,
        message_type: str = "general"
    ) -> bool:
        """
        Send a message from one agent to another.
        
        Args:
            from_agent_id: Sender agent ID
            to_agent_id: Recipient agent ID
            message: Message content
            message_type: Type of message
            
        Returns:
            True if message was sent successfully
        """
        with self._lock:
            if from_agent_id not in self.agents:
                logger.warning(f"Unknown sender agent: {from_agent_id}")
                return False
            
            if to_agent_id not in self.agents and to_agent_id != "broadcast":
                logger.warning(f"Unknown recipient agent: {to_agent_id}")
                return False
            
            message_entry = {
                'timestamp': dt_now(),
                'from': from_agent_id,
                'to': to_agent_id,
                'type': message_type,
                'message': message
            }
            
            self.messages.append(message_entry)
            
            # Keep only last 1000 messages
            if len(self.messages) > 1000:
                self.messages = self.messages[-1000:]
            
            logger.debug(f"Message sent from {from_agent_id} to {to_agent_id}")
            return True
    
    def get_messages(
        self,
        agent_id: str,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a specific agent.
        
        Args:
            agent_id: Agent ID to get messages for
            since: Optional timestamp to get messages since
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        with self._lock:
            result = []
            for msg in reversed(self.messages):
                # Check if message is for this agent (direct or broadcast)
                if msg['to'] == agent_id or msg['to'] == "broadcast":
                    # Check timestamp filter
                    if since and msg['timestamp'] < since:
                        continue
                    
                    result.append({
                        'timestamp': msg['timestamp'].isoformat(),
                        'from': msg['from'],
                        'to': msg['to'],
                        'type': msg['type'],
                        'message': msg['message']
                    })
                    
                    if len(result) >= limit:
                        break
            
            return list(reversed(result))
    
    def get_status_history(
        self,
        agent_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get status update history for an agent.
        
        Args:
            agent_id: Agent ID
            limit: Maximum number of updates to return
            
        Returns:
            List of status update dictionaries
        """
        with self._lock:
            if agent_id not in self.status_updates:
                return []
            
            updates = self.status_updates[agent_id][-limit:]
            
            return [
                {
                    'timestamp': update['timestamp'].isoformat(),
                    'status': update['status'],
                    'data': update['data']
                }
                for update in updates
            ]
    
    def broadcast_message(
        self,
        from_agent_id: str,
        message: Any,
        message_type: str = "broadcast"
    ) -> bool:
        """
        Broadcast a message to all agents.
        
        Args:
            from_agent_id: Sender agent ID
            message: Message content
            message_type: Type of message
            
        Returns:
            True if broadcast was successful
        """
        return self.send_message(
            from_agent_id=from_agent_id,
            to_agent_id="broadcast",
            message=message,
            message_type=message_type
        )
    
    def clear_old_messages(self, days: int = 7) -> int:
        """
        Clear messages older than specified days.
        
        Args:
            days: Number of days to keep messages
            
        Returns:
            Number of messages cleared
        """
        with self._lock:
            from datetime import timedelta
            cutoff_time = dt_now() - timedelta(days=days)
            
            old_count = len(self.messages)
            self.messages = [
                msg for msg in self.messages
                if msg['timestamp'] >= cutoff_time
            ]
            
            cleared = old_count - len(self.messages)
            logger.info(f"Cleared {cleared} old messages")
            return cleared
