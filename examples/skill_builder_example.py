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
    
    from SkillBuilder import SkillBuilder
    
    builder = SkillBuilder()
    
    # Create a simple skill from a prompt
    result = builder.create_simple_skill(
        skill_name='HanoiWeatherChecker',
        prompt='Check the current weather in Hanoi, Vietnam'
    )
    
    print(f"\nResult: {result}")
    
    # Test the generated skill
    if 'successfully' in result:
        print("\n--- Testing Generated Skill ---")
        from HanoiWeatherChecker import HanoiWeatherChecker
        
        checker = HanoiWeatherChecker()
        weather_result = checker.hanoi_weather_checker('Get current weather')
        print(f"Skill output: {weather_result}")


def example_2_advanced_skill():
    """Example 2: Create an advanced skill with specific parameters and implementation."""
    print("\n" + "="*60)
    print("Example 2: Create Advanced Weather API Skill")
    print("="*60)
    
    from SkillBuilder import SkillBuilder
    
    builder = SkillBuilder()
    
    # Define parameters for the skill
    parameters = json.dumps([
        {
            'name': 'city',
            'type': 'str',
            'description': 'Name of the city to check weather'
        },
        {
            'name': 'country_code',
            'type': 'str',
            'description': 'Two-letter country code (e.g., VN, US)'
        },
        {
            'name': 'units',
            'type': 'str',
            'description': 'Temperature units: metric (Celsius) or imperial (Fahrenheit)'
        }
    ])
    
    # Define the implementation
    implementation = '''import os
# In a real implementation, you would use an API key from environment
# api_key = os.environ.get('OPENWEATHER_API_KEY', 'demo-key')
api_key = 'demo-key'

# Construct API URL
location = f"{city},{country_code}"
url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units={units}"

# In a real implementation, you would make the actual API call:
# import requests
# response = requests.get(url)
# weather_data = response.json()

# For this demo, we'll return the URL that would be called
result = f"Weather API endpoint: {url}\\n"
result += f"City: {city}, Country: {country_code}\\n"
result += f"Units: {units}\\n"
result += "In production, this would fetch real weather data."

IOMsg.send_msg(result)
return result'''
    
    # Generate the skill
    result = builder.generate_skill(
        skill_name='WeatherAPISkill',
        description='Get weather information for any city using OpenWeatherMap API',
        method_name='get_weather',
        parameters=parameters,
        implementation=implementation
    )
    
    print(f"\nResult: {result}")
    
    # Test the generated skill
    if 'successfully' in result:
        print("\n--- Testing Generated Skill ---")
        from WeatherAPISkill import WeatherAPISkill
        
        api = WeatherAPISkill()
        
        # Test with Hanoi
        hanoi_weather = api.get_weather(
            city='Hanoi',
            country_code='VN',
            units='metric'
        )
        print(f"\nHanoi Weather:\n{hanoi_weather}")
        
        # Test with another city
        tokyo_weather = api.get_weather(
            city='Tokyo',
            country_code='JP',
            units='metric'
        )
        print(f"\nTokyo Weather:\n{tokyo_weather}")


def example_3_test_sandbox():
    """Example 3: Test skill code in sandbox before saving."""
    print("\n" + "="*60)
    print("Example 3: Test Skill Code in Sandbox")
    print("="*60)
    
    from SkillBuilder import SkillBuilder
    
    builder = SkillBuilder()
    
    # Example skill code to test
    test_code = '''from pydantic import BaseModel
from sonagent.rpc import IOMsg

class CalculatorSkill(BaseModel):
    """Simple calculator skill."""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        result = a + b
        IOMsg.send_msg(f"Adding {a} + {b} = {result}")
        return result
    
    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        result = a * b
        IOMsg.send_msg(f"Multiplying {a} * {b} = {result}")
        return result
'''
    
    print("Testing skill code in sandbox...")
    result = builder.test_skill_code(test_code)
    print(f"\nTest Result: {result}")


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
    
    # Mock IOMsg for examples
    mock_iomsg()
    
    try:
        # Run examples
        example_1_simple_skill()
        example_2_advanced_skill()
        example_3_test_sandbox()
        example_4_reload_skills()
        
        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60)
        
        print("\n--- Next Steps ---")
        print("1. Check the generated skills in user_data/skills/")
        print("2. Edit the generated skills to add real implementations")
        print("3. Use the skills in your agent by calling reload_skills()")
        print("4. The agent will automatically load and index new skills")
        
    except Exception as e:
        print(f"\n!!! Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
