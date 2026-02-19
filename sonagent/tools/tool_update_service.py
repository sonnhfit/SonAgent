"""
Tool Update Service - Manages dynamic tool updates for teams and agents.
This service monitors ToolRegistry for changes and updates registered teams/agents.
"""
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ToolUpdateSubscriber:
    """Subscriber information for tool updates."""
    name: str
    update_callback: Callable[[List[Any]], None]  # Callback to update tools
    description: str = ""
    last_updated: float = 0.0


class ToolUpdateService:
    """
    Service that manages dynamic tool updates for teams and agents.
    
    This service:
    1. Monitors ToolRegistry for changes
    2. Maintains a list of subscribers (teams/agents) that need tool updates
    3. Calls update callbacks when tools change
    4. Provides manual update triggers
    """
    
    def __init__(self, tool_registry, scan_interval: int = 30):
        """
        Initialize the Tool Update Service.
        
        Args:
            tool_registry: Instance of ToolRegistry
            scan_interval: How often to check for tool changes (seconds)
        """
        self.tool_registry = tool_registry
        self.scan_interval = scan_interval
        
        # Subscribers registry
        self.subscribers: Dict[str, ToolUpdateSubscriber] = {}
        
        # Monitoring thread
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()
        
        # Track last known tool state
        self.last_tool_count = 0
        self.last_tool_names: Set[str] = set()
        
        logger.info(f"ToolUpdateService initialized with scan interval: {scan_interval}s")
    
    def start_monitoring(self) -> None:
        """Start the background monitoring thread."""
        if self.monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="ToolUpdateMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("Tool update monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the background monitoring thread."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
            self.monitor_thread = None
        logger.info("Tool update monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self.monitoring:
            try:
                self.check_and_update()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
            
            # Sleep for scan interval
            time.sleep(self.scan_interval)
    
    def check_and_update(self) -> bool:
        """
        Check for tool changes and update subscribers if needed.
        
        Returns:
            True if updates were performed, False otherwise
        """
        with self.lock:
            # Force scan for changes
            changed = self.tool_registry.scan_and_load_tools(force=False)
            
            if not changed:
                return False
            
            # Get current tools
            current_tools = self.tool_registry.get_tools()
            current_tool_names = {tool["name"] for tool in current_tools}
            
            # Check if tools actually changed
            if (len(current_tools) == self.last_tool_count and 
                current_tool_names == self.last_tool_names):
                return False
            
            # Update state
            self.last_tool_count = len(current_tools)
            self.last_tool_names = current_tool_names
            
            # Get tool functions for subscribers
            tool_functions = []
            for tool_info in current_tools:
                tool_func = self.tool_registry.get_tool_function(tool_info["name"])
                if tool_func:
                    tool_functions.append(tool_func)
            
            # Update all subscribers
            self._update_all_subscribers(tool_functions)
            
            logger.info(f"Tools updated: {len(tool_functions)} tools, {len(self.subscribers)} subscribers notified")
            return True
    
    def _update_all_subscribers(self, tool_functions: List[Any]) -> None:
        """Update all subscribers with new tools."""
        for subscriber_name, subscriber in list(self.subscribers.items()):
            try:
                subscriber.update_callback(tool_functions)
                subscriber.last_updated = time.time()
                logger.debug(f"Updated subscriber: {subscriber_name}")
            except Exception as e:
                logger.error(f"Failed to update subscriber {subscriber_name}: {e}", exc_info=True)
    
    def register_subscriber(self, name: str, update_callback: Callable[[List[Any]], None], 
                           description: str = "") -> bool:
        """
        Register a subscriber for tool updates.
        
        Args:
            name: Unique name for the subscriber
            update_callback: Function to call with new tools list
            description: Optional description
            
        Returns:
            True if registered successfully, False if name already exists
        """
        with self.lock:
            if name in self.subscribers:
                logger.warning(f"Subscriber already exists: {name}")
                return False
            
            subscriber = ToolUpdateSubscriber(
                name=name,
                update_callback=update_callback,
                description=description,
                last_updated=0.0
            )
            
            self.subscribers[name] = subscriber
            logger.info(f"Registered subscriber: {name} - {description}")
            
            # Immediately update with current tools
            self._update_subscriber_immediately(subscriber)
            
            return True
    
    def _update_subscriber_immediately(self, subscriber: ToolUpdateSubscriber) -> None:
        """Update a single subscriber immediately with current tools."""
        try:
            # Get current tools
            current_tools = self.tool_registry.get_tools()
            tool_functions = []
            for tool_info in current_tools:
                tool_func = self.tool_registry.get_tool_function(tool_info["name"])
                if tool_func:
                    tool_functions.append(tool_func)
            
            # Update subscriber
            subscriber.update_callback(tool_functions)
            subscriber.last_updated = time.time()
            
            logger.debug(f"Immediately updated subscriber: {subscriber.name}")
        except Exception as e:
            logger.error(f"Failed to immediately update subscriber {subscriber.name}: {e}", exc_info=True)
    
    def unregister_subscriber(self, name: str) -> bool:
        """
        Unregister a subscriber.
        
        Args:
            name: Subscriber name
            
        Returns:
            True if unregistered, False if not found
        """
        with self.lock:
            if name not in self.subscribers:
                logger.warning(f"Subscriber not found: {name}")
                return False
            
            del self.subscribers[name]
            logger.info(f"Unregistered subscriber: {name}")
            return True
    
    def get_subscriber_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a subscriber.
        
        Args:
            name: Subscriber name
            
        Returns:
            Subscriber information or None if not found
        """
        with self.lock:
            if name not in self.subscribers:
                return None
            
            subscriber = self.subscribers[name]
            return {
                "name": subscriber.name,
                "description": subscriber.description,
                "last_updated": subscriber.last_updated,
                "last_updated_human": time.ctime(subscriber.last_updated) if subscriber.last_updated > 0 else "Never"
            }
    
    def list_subscribers(self) -> List[Dict[str, Any]]:
        """
        List all registered subscribers.
        
        Returns:
            List of subscriber information
        """
        with self.lock:
            result = []
            for name, subscriber in self.subscribers.items():
                result.append({
                    "name": name,
                    "description": subscriber.description,
                    "last_updated": subscriber.last_updated,
                    "last_updated_human": time.ctime(subscriber.last_updated) if subscriber.last_updated > 0 else "Never"
                })
            return result
    
    def force_update(self) -> bool:
        """
        Force an immediate check and update of all subscribers.
        
        Returns:
            True if updates were performed, False otherwise
        """
        logger.info("Forcing tool update check")
        return self.check_and_update()
    
    def update_single_subscriber(self, name: str) -> bool:
        """
        Update a single subscriber immediately.
        
        Args:
            name: Subscriber name
            
        Returns:
            True if updated, False if not found
        """
        with self.lock:
            if name not in self.subscribers:
                logger.warning(f"Subscriber not found: {name}")
                return False
            
            subscriber = self.subscribers[name]
            self._update_subscriber_immediately(subscriber)
            return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get service status information.
        
        Returns:
            Status dictionary
        """
        with self.lock:
            return {
                "monitoring": self.monitoring,
                "scan_interval": self.scan_interval,
                "subscriber_count": len(self.subscribers),
                "last_tool_count": self.last_tool_count,
                "last_tool_names": list(self.last_tool_names),
                "subscribers": self.list_subscribers()
            }


# Singleton instance
_instance: Optional[ToolUpdateService] = None


def get_tool_update_service(tool_registry=None, scan_interval: int = 30) -> ToolUpdateService:
    """
    Get or create the singleton ToolUpdateService instance.
    
    Args:
        tool_registry: ToolRegistry instance (required for first call)
        scan_interval: Scan interval in seconds
        
    Returns:
        ToolUpdateService instance
    """
    global _instance
    
    if _instance is None:
        if tool_registry is None:
            raise ValueError("tool_registry is required for first initialization")
        
        _instance = ToolUpdateService(tool_registry, scan_interval)
    
    return _instance


def register_team_for_tool_updates(team, name: str, description: str = "") -> bool:
    """
    Convenience function to register a team for tool updates.
    
    Args:
        team: Team instance (must have set_tools method)
        name: Unique name for the team
        description: Optional description
        
    Returns:
        True if registered successfully
    """
    service = get_tool_update_service()
    
    def update_callback(tools: List[Any]) -> None:
        """Update team's tools."""
        try:
            team.set_tools(tools)
            logger.info(f"Updated tools for team: {name}")
        except Exception as e:
            logger.error(f"Failed to update tools for team {name}: {e}", exc_info=True)
    
    return service.register_subscriber(name, update_callback, description)


def register_agent_for_tool_updates(agent, name: str, description: str = "") -> bool:
    """
    Convenience function to register an agent for tool updates.
    
    Args:
        agent: Agent instance (must have set_tools method)
        name: Unique name for the agent
        description: Optional description
        
    Returns:
        True if registered successfully
    """
    service = get_tool_update_service()
    
    def update_callback(tools: List[Any]) -> None:
        """Update agent's tools."""
        try:
            agent.set_tools(tools)
            logger.info(f"Updated tools for agent: {name}")
        except Exception as e:
            logger.error(f"Failed to update tools for agent {name}: {e}", exc_info=True)
    
    return service.register_subscriber(name, update_callback, description)


if __name__ == "__main__":
    # Example usage
    import sys
    sys.path.insert(0, ".")
    
    from sonagent.tools.tool_registry import ToolRegistry
    
    # Create a mock config
    config = {"user_data_dir": "user_data"}
    
    # Initialize registry and service
    registry = ToolRegistry(config)
    service = ToolUpdateService(registry, scan_interval=10)
    
    # Start monitoring
    service.start_monitoring()
    
    print("Tool Update Service started")
    print(f"Status: {service.get_status()}")
    
    # Keep running for demonstration
    try:
        while True:
            time.sleep(60)
            print(f"Service status: {service.get_status()}")
    except KeyboardInterrupt:
        print("\nStopping service...")
        service.stop_monitoring()