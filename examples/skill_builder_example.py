#!/usr/bin/env python
"""
Example demonstrating dynamic skill generation with SkillBuilder.

This example shows how to:
1. Generate a simple skill from a natural language prompt
2. Generate an advanced skill with specific parameters and implementation
3. Test the generated skills in a sandbox
4. Save skills to the skills directory
5. Reload and use the generated skills

Usage:
    python examples/skill_builder_example.py
"""
import json
import os
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'user_data' / 'skills'))

# Set environment variable for user data directory
os.environ['USER_DATA_DIR'] = str(Path(__file__).parent.parent / 'user_data')


def mock_iomsg():
    """Mock IOMsg for testing without telegram."""
    class MockIOMsg:
        @staticmethod
        def send_msg(msg):
            print(f"[IOMsg] {msg}")
    
    import sonagent.rpc as rpc_module
    rpc_module.IOMsg = MockIOMsg


def example_1_simple_skill():
    """Example 1: Create a simple skill from a natural language prompt."""
    print("\n" + "="*60)
    print("Example 1: Create Simple Weather Skill from Prompt")
    print("="*60)
    
    print("\nSKIPPED: SkillBuilder module has been removed")
    print("This example would have created a HanoiWeatherChecker skill")


def example_2_advanced_skill():
    """Example 2: Create an advanced skill with specific parameters and implementation."""
    print("\n" + "="*60)
    print("Example 2: Create Advanced Weather API Skill")
    print("="*60)
    
    print("\nSKIPPED: SkillBuilder module has been removed")
    print("This example would have created a WeatherAPISkill with parameters")


def example_3_test_sandbox():
    """Example 3: Test skill code in sandbox before saving."""
    print("\n" + "="*60)
    print("Example 3: Test Skill Code in Sandbox")
    print("="*60)
    
    print("\nSKIPPED: SkillBuilder module has been removed")
    print("This example would have tested skill code in a sandbox")


def example_4_reload_skills():
    """Example 4: Demonstrate skill reloading."""
    print("\n" + "="*60)
    print("Example 4: Reload Skills at Runtime")
    print("="*60)
    
    # Create config
    config = {
        'user_data_dir': str(Path(__file__).parent.parent / 'user_data'),
        'memory_path': str(Path(__file__).parent.parent / 'user_data' / 'memory'),
    }
    
    from sonagent.skills.skills_manager import SkillsManager
    
    class MockSonAgent:
        def __init__(self):
            self.config = config
    
    mock_agent = MockSonAgent()
    skills_manager = SkillsManager(mock_agent)
    
    print("\nScanning skills directory...")
    skill_names = skills_manager.scan_skills_directory()
    print(f"Found skills: {', '.join(skill_names)}")
    
    print("\nLoading skills...")
    skills_manager.load_skills()
    loaded_skills = skills_manager.get_all_skills()
    print(f"Loaded {len(loaded_skills)} skills:")
    for skill in loaded_skills:
        print(f"  - {skill.__class__.__name__}")
    
    print("\n--- Skills can be reloaded at runtime ---")
    print("If you add a new skill file, call reload_skills() to load it.")
    
    # Demonstrate reload
    print("\nReloading skills...")
    skills_manager.reload_skills()
    reloaded_skills = skills_manager.get_all_skills()
    print(f"Reloaded {len(reloaded_skills)} skills")


def main():
    """Run all examples."""
    print("="*60)
    print("SkillBuilder Examples - Dynamic Skill Generation")
    print("="*60)
    print("\nNOTE: SkillBuilder module has been removed from the project.")
    print("These examples are now placeholders showing what would have been demonstrated.")
    print("="*60)
    
    # Mock IOMsg for examples
    mock_iomsg()
    
    try:
        # Run examples
        example_1_simple_skill()
        example_2_advanced_skill()
        example_3_test_sandbox()
        example_4_reload_skills()
        
        print("\n" + "="*60)
        print("Examples completed (as placeholders)")
        print("="*60)
        
        print("\n--- Note ---")
        print("The SkillBuilder module was removed from the project.")
        print("Dynamic skill generation functionality may be reimplemented differently.")
        
    except Exception as e:
        print(f"\n!!! Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
