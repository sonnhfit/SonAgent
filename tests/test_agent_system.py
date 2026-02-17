"""
Tests for the agent system.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from sonagent.agent_registry import AgentRegistry
from sonagent.agents.base_agent import BaseAgent
from sonagent.agents.main_agent import MainAgent


class TestAgentRegistry:
    """Test agent registry functionality."""
    
    def test_registry_initialization(self):
        """Test that registry initializes correctly."""
        registry = AgentRegistry()
        assert registry is not None
        assert len(registry.agents) == 0
        assert len(registry.messages) == 0
    
    def test_register_agent(self):
        """Test agent registration."""
        registry = AgentRegistry()
        
        # Create mock agent
        mock_agent = Mock()
        mock_agent.agent_id = "test_agent"
        mock_agent.agent_name = "Test Agent"
        mock_agent.status = "initialized"
        
        # Register agent
        registry.register_agent(mock_agent)
        
        # Verify registration
        assert "test_agent" in registry.agents
        assert registry.agents["test_agent"]["agent_name"] == "Test Agent"
    
    def test_unregister_agent(self):
        """Test agent unregistration."""
        registry = AgentRegistry()
        
        # Create and register mock agent
        mock_agent = Mock()
        mock_agent.agent_id = "test_agent"
        mock_agent.agent_name = "Test Agent"
        mock_agent.status = "initialized"
        registry.register_agent(mock_agent)
        
        # Unregister
        result = registry.unregister_agent("test_agent")
        
        # Verify unregistration
        assert result is True
        assert "test_agent" not in registry.agents
    
    def test_send_message(self):
        """Test sending messages between agents."""
        registry = AgentRegistry()
        
        # Register two agents
        agent1 = Mock()
        agent1.agent_id = "agent1"
        agent1.agent_name = "Agent 1"
        agent1.status = "initialized"
        
        agent2 = Mock()
        agent2.agent_id = "agent2"
        agent2.agent_name = "Agent 2"
        agent2.status = "initialized"
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        # Send message
        result = registry.send_message(
            from_agent_id="agent1",
            to_agent_id="agent2",
            message="Hello",
            message_type="greeting"
        )
        
        # Verify message sent
        assert result is True
        assert len(registry.messages) == 1
        assert registry.messages[0]["from"] == "agent1"
        assert registry.messages[0]["to"] == "agent2"
        assert registry.messages[0]["message"] == "Hello"
    
    def test_get_messages(self):
        """Test retrieving messages for an agent."""
        registry = AgentRegistry()
        
        # Register agents
        agent1 = Mock()
        agent1.agent_id = "agent1"
        agent1.agent_name = "Agent 1"
        agent1.status = "initialized"
        
        agent2 = Mock()
        agent2.agent_id = "agent2"
        agent2.agent_name = "Agent 2"
        agent2.status = "initialized"
        
        registry.register_agent(agent1)
        registry.register_agent(agent2)
        
        # Send messages
        registry.send_message("agent1", "agent2", "Message 1")
        registry.send_message("agent1", "agent2", "Message 2")
        
        # Get messages for agent2
        messages = registry.get_messages("agent2", limit=10)
        
        # Verify messages
        assert len(messages) == 2
        assert messages[0]["message"] == "Message 1"
        assert messages[1]["message"] == "Message 2"


class TestMainAgent:
    """Test main agent functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        return {
            "user_data_dir": "/tmp/test_user_data",
            "llm": {
                "api_type": "openai",
                "model": "gpt-3.5-turbo"
            }
        }
    
    @pytest.fixture
    def mock_skills_manager(self):
        """Mock skills manager."""
        manager = Mock()
        manager.get_all_skills.return_value = []
        manager.load_skills.return_value = None
        return manager
    
    @pytest.fixture
    def mock_registry(self):
        """Mock agent registry."""
        return AgentRegistry()
    
    @patch('sonagent.agents.base_agent.AgentBrain')
    def test_main_agent_initialization(self, mock_brain, mock_config, mock_skills_manager, mock_registry):
        """Test main agent initialization."""
        # Create main agent
        main_agent = MainAgent(
            config=mock_config,
            skills_manager=mock_skills_manager,
            agent_registry=mock_registry
        )
        
        # Verify initialization
        assert main_agent.agent_id == "main_agent"
        assert main_agent.agent_name == "Main Agent"
        assert main_agent.agent_registry == mock_registry
        assert main_agent.running is False
    
    @patch('sonagent.agents.base_agent.AgentBrain')
    @pytest.mark.asyncio
    async def test_create_task(self, mock_brain, mock_config, mock_skills_manager, mock_registry):
        """Test task creation."""
        # Create main agent
        main_agent = MainAgent(
            config=mock_config,
            skills_manager=mock_skills_manager,
            agent_registry=mock_registry
        )
        
        # Mock Task.create_task
        with patch('sonagent.agents.main_agent.Task') as mock_task:
            mock_task_instance = Mock()
            mock_task_instance.id = 1
            mock_task.create_task.return_value = mock_task_instance
            
            # Create task
            result = await main_agent._create_task({
                'content': 'Test task',
                'priority': 5,
                'agent_id': 'main_agent'
            })
            
            # Verify task creation
            assert "Task created successfully" in result
            assert "Task ID: 1" in result


def test_skills_manager_agent_specific():
    """Test that skills manager supports agent-specific skills."""
    from sonagent.skills.skills_manager import SkillsManager
    from pathlib import Path
    
    # Mock sonagent object
    mock_sonagent = Mock()
    mock_sonagent.config = {
        'user_data_dir': '/tmp/test_user_data'
    }
    
    # Create skills manager with agent_id
    skills_manager = SkillsManager(mock_sonagent, agent_id="test_agent")
    
    # Verify agent-specific directory
    expected_dir = Path('/tmp/test_user_data/skills/test_agent')
    assert skills_manager.skills_dir == expected_dir
    assert skills_manager.agent_id == "test_agent"


def test_skills_manager_shared():
    """Test that skills manager supports shared skills."""
    from sonagent.skills.skills_manager import SkillsManager
    from pathlib import Path
    
    # Mock sonagent object
    mock_sonagent = Mock()
    mock_sonagent.config = {
        'user_data_dir': '/tmp/test_user_data'
    }
    
    # Create skills manager without agent_id
    skills_manager = SkillsManager(mock_sonagent)
    
    # Verify shared directory
    expected_dir = Path('/tmp/test_user_data/skills')
    assert skills_manager.skills_dir == expected_dir
    assert skills_manager.agent_id is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
