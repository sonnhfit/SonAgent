"""
Test that tool methods in MainTeamAgent can be called directly.

This test verifies the fix for the bug where @tool() decorated methods
were not callable directly within the class.
"""
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestMainTeamToolsMockable(unittest.TestCase):
    """Test that tool methods exist and are callable without @tool() decorator."""
    
    @patch('sonagent.agents.main_team.Agent')
    @patch('sonagent.agents.main_team.Team')
    @patch('sonagent.agents.main_team.SqliteDb')
    @patch('sonagent.agents.main_team.OpenAIResponses')
    def test_tool_methods_are_callable(self, mock_openai, mock_db, mock_team, mock_agent):
        """Test that base tool methods are regular methods and can be called."""
        from sonagent.agents.main_team import MainTeamAgent
        
        # Mock the database and other dependencies
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        
        # Create instance
        config = {}
        agent = MainTeamAgent(config, db_path=":memory:")
        
        # Verify that tool methods are callable (not Function objects)
        # These should be regular methods, not wrapped by @tool()
        self.assertTrue(callable(agent.save_chat_message_tool))
        self.assertTrue(callable(agent.extract_tom_tool))
        self.assertTrue(callable(agent.respond_to_user_tool))
        self.assertTrue(callable(agent.get_chat_history_tool))
        
        # Check that they are bound methods, not Function objects
        import inspect
        self.assertTrue(inspect.ismethod(agent.save_chat_message_tool))
        self.assertTrue(inspect.ismethod(agent.extract_tom_tool))
        self.assertTrue(inspect.ismethod(agent.respond_to_user_tool))
        self.assertTrue(inspect.ismethod(agent.get_chat_history_tool))
        
        # Verify wrapper methods still exist (these should have @tool() decorator)
        self.assertTrue(hasattr(agent, '_save_chat_message_tool_wrapper'))
        self.assertTrue(hasattr(agent, '_extract_tom_tool_wrapper'))
        self.assertTrue(hasattr(agent, '_respond_to_user_tool_wrapper'))
        self.assertTrue(hasattr(agent, '_get_chat_history_tool_wrapper'))


if __name__ == '__main__':
    unittest.main()
