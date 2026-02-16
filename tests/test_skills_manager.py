"""
Tests for SkillsManager and standard skills copying.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sonagent.skills.skills_manager import SkillsManager


class TestSkillsManager(unittest.TestCase):
    """Test SkillsManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.user_data_dir = Path(self.test_dir) / "user_data"
        self.user_data_dir.mkdir()
        self.skills_dir = self.user_data_dir / "skills"
        
        # Create a mock sonagent object
        self.mock_sonagent = Mock()
        self.mock_sonagent.config = {
            'user_data_dir': str(self.user_data_dir)
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    def test_copy_standard_skills_to_empty_directory(self):
        """Test that standard skills are copied to an empty skills directory."""
        # Create SkillsManager - this should trigger the copy
        skills_manager = SkillsManager(self.mock_sonagent)
        
        # Check that the skills directory was created
        self.assertTrue(self.skills_dir.exists())
        
        # Check that skills were copied
        skill_files = [f for f in self.skills_dir.iterdir() 
                      if f.suffix == '.py' and not f.name.startswith('__')]
        
        # Should have copied standard skills
        self.assertGreater(len(skill_files), 0, "Standard skills should have been copied")
        
        # Check for specific known skills
        skill_names = [f.stem for f in skill_files]
        self.assertIn('TextPrinter', skill_names, "TextPrinter should be in standard skills")
    
    def test_skip_copy_when_skills_exist(self):
        """Test that standard skills are not copied when skills already exist."""
        # Create the skills directory with a dummy skill
        self.skills_dir.mkdir(parents=True)
        dummy_skill = self.skills_dir / "DummySkill.py"
        dummy_skill.write_text("# Dummy skill\nclass DummySkill:\n    pass\n")
        
        # Count initial files
        initial_count = len([f for f in self.skills_dir.iterdir() 
                           if f.suffix == '.py' and not f.name.startswith('__')])
        
        # Create SkillsManager - should NOT copy because directory is not empty
        skills_manager = SkillsManager(self.mock_sonagent)
        
        # Check that no new skills were added
        final_count = len([f for f in self.skills_dir.iterdir() 
                         if f.suffix == '.py' and not f.name.startswith('__')])
        
        self.assertEqual(initial_count, final_count, 
                        "Should not copy skills when directory already has skills")
        self.assertEqual(final_count, 1, "Should still have only the dummy skill")
    
    def test_scan_skills_directory(self):
        """Test scanning the skills directory."""
        # Create some test skill files
        self.skills_dir.mkdir(parents=True)
        (self.skills_dir / "Skill1.py").write_text("class Skill1: pass")
        (self.skills_dir / "Skill2.py").write_text("class Skill2: pass")
        (self.skills_dir / "__init__.py").write_text("")  # Should be ignored
        
        # Create SkillsManager (will try to copy but should skip)
        skills_manager = SkillsManager(self.mock_sonagent)
        
        # Scan the directory
        skill_names = skills_manager.scan_skills_directory()
        
        # Should find 2 skills (excluding __init__.py)
        self.assertEqual(len(skill_names), 2)
        self.assertIn('Skill1', skill_names)
        self.assertIn('Skill2', skill_names)
        self.assertNotIn('__init__', skill_names)


if __name__ == '__main__':
    unittest.main()
