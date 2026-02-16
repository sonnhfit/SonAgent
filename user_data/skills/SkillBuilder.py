import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from sonagent.rpc import IOMsg
from sonagent.tools.sandbox_executor import SandboxExecutor
from sonagent.tools.skill_generator import SkillGenerator

logger = logging.getLogger(__name__)


class SkillBuilder(BaseModel):
    """
    SkillBuilder.generate_skill
    description: Dynamically generate a new skill and save it to the skills directory
    args:
        - skill_name: Name of the skill class (e.g., "WeatherChecker")
        - description: Description of what the skill does
        - method_name: Name of the main method (optional, defaults to snake_case of skill_name)
        - parameters: JSON string of parameters list, each with 'name', 'type', 'description'
        - implementation: Python code for the method implementation (optional)
        
    SkillBuilder.test_skill_code
    description: Test skill code in a sandbox environment before saving
    args:
        - code: Python code to test
        
    SkillBuilder.create_simple_skill
    description: Create a simple skill from a natural language prompt
    args:
        - skill_name: Name for the skill
        - prompt: Natural language description of what the skill should do
    
    IMPORTANT:
    - All helper/private methods in generated skills MUST start with underscore (_) prefix
    - Only public methods (without _ prefix) will be exposed as LangChain tools
    - Example: def calculate(): is public, def _validate_input(): is private
    - a skill only have one publich method that use for tool with function docs string
    """

    def _parse_parameters(self, parameters: Optional[str]) -> Optional[List[Dict]]:
        """Parse JSON parameters string into a list of parameter dictionaries."""
        if not parameters:
            return None
        try:
            return json.loads(parameters)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid parameters JSON: {str(e)}")
    
    def _get_skills_directory(self) -> Path:
        """Get the skills directory path."""
        user_data_dir = os.environ.get('USER_DATA_DIR', 'user_data')
        return Path(user_data_dir) / 'skills'
    
    def _validate_and_test_code(self, code: str) -> Dict[str, Any]:
        """Test skill code in sandbox and return results."""
        sandbox = SandboxExecutor()
        return sandbox.test_skill_code(code)
    
    def generate_skill(
        self,
        skill_name: str,
        description: str,
        method_name: Optional[str] = None,
        parameters: Optional[str] = None,
        implementation: Optional[str] = None
    ) -> str:
        """
        Generate a new skill and save it to the skills directory.
        
        Args:
            skill_name (str): Name of the skill class (e.g., "WeatherChecker")
            description (str): Description of what the skill does
            method_name (Optional[str]): Name of the main method
            parameters (Optional[str]): JSON string of parameters
            implementation (Optional[str]): Python code for the method implementation
        
        Returns:
            str: Status message with path to saved skill or error message
        """
        try:
            logger.info(f"[SkillBuilder] Starting generate_skill - skill_name: {skill_name}, description: {description}")
            
            # Parse parameters if provided
            params_list = self._parse_parameters(parameters)
            
            # Create skill generator
            generator = SkillGenerator()
            logger.debug("[SkillBuilder] Created SkillGenerator instance")
            
            # Generate skill code
            logger.info(f"[SkillBuilder] Calling SkillGenerator.generate_skill for skill: {skill_name}")
            code = generator.generate_skill(
                skill_name=skill_name,
                description=description,
                method_name=method_name,
                parameters=params_list,
                implementation=implementation
            )
            logger.debug(f"[SkillBuilder] Generated code length: {len(code)} chars")
            
            IOMsg.send_msg(f"Generated skill code:\n```python\n{code}\n```")
            
            # Test in sandbox first
            logger.debug("[SkillBuilder] Testing skill code in sandbox")
            test_result = self._validate_and_test_code(code)
            logger.debug(f"[SkillBuilder] Sandbox test result: success={test_result.get('success')}")
            
            if not test_result['success']:
                error_msg = f"Error: Skill code failed validation:\n{test_result.get('error', 'Unknown error')}"
                logger.error(f"[SkillBuilder] Sandbox validation failed: {test_result.get('error')}")
                IOMsg.send_msg(error_msg)
                return error_msg
            
            logger.info("[SkillBuilder] Skill code validated successfully in sandbox")
            IOMsg.send_msg("✓ Skill code validated successfully in sandbox")
            
            # Get skills directory from environment or use default
            skills_dir = self._get_skills_directory()
            logger.debug(f"[SkillBuilder] Skills directory: {skills_dir}")
            
            # Save skill
            skill_file = generator.save_skill(code, skill_name, skills_dir)
            logger.info(f"[SkillBuilder] Skill saved to: {skill_file}")
            
            success_msg = f"✓ Skill '{skill_name}' created successfully at: {skill_file}\n"
            success_msg += "To use this skill, reload skills with the reload_skills command."
            
            IOMsg.send_msg(success_msg)
            return success_msg
            
        except Exception as e:
            logger.exception(f"[SkillBuilder] Error generating skill: {str(e)}")
            error_msg = f"Error generating skill: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg
    
    def test_skill_code(self, code: str) -> str:
        """
        Test skill code in a sandbox environment.
        
        Args:
            code (str): Python skill code to test
        
        Returns:
            str: Test results
        """
        try:
            logger.info(f"[SkillBuilder] Starting test_skill_code - code length: {len(code)} chars")
            
            logger.debug("[SkillBuilder] Executing sandbox test")
            result = self._validate_and_test_code(code)
            logger.debug(f"[SkillBuilder] Test result: success={result.get('success')}")
            
            if result['success']:
                output = "✓ Skill code is valid and executed successfully\n"
                if result.get('output'):
                    output += f"\nOutput:\n{result['output']}"
                logger.info("[SkillBuilder] Skill code test passed")
                IOMsg.send_msg(output)
                return output
            else:
                error = f"✗ Skill code validation failed:\n{result.get('error', 'Unknown error')}"
                logger.error(f"[SkillBuilder] Skill code test failed: {result.get('error')}")
                IOMsg.send_msg(error)
                return error
                
        except Exception as e:
            logger.exception(f"[SkillBuilder] Error testing skill code: {str(e)}")
            error_msg = f"Error testing skill code: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg
    
    def create_simple_skill(self, skill_name: str, prompt: str) -> str:
        """
        Create a simple skill from a natural language prompt.
        
        Args:
            skill_name (str): Name for the skill (e.g., "WeatherChecker")
            prompt (str): Natural language description of what the skill should do
        
        Returns:
            str: Status message with path to saved skill or error message
        """
        try:
            logger.info(f"[SkillBuilder] Starting create_simple_skill - skill_name: {skill_name}, prompt: {prompt}")
            
            # Create skill generator
            generator = SkillGenerator()
            logger.debug("[SkillBuilder] Created SkillGenerator instance")
            
            # Generate simple skill from prompt
            logger.info(f"[SkillBuilder] Generating simple skill from prompt")
            code = generator.generate_simple_skill_from_prompt(
                prompt=prompt,
                skill_name=skill_name
            )
            logger.debug(f"[SkillBuilder] Generated code length: {len(code)} chars")
            
            IOMsg.send_msg(f"Generated skill code from prompt:\n```python\n{code}\n```")
            
            # Test in sandbox
            logger.debug("[SkillBuilder] Testing skill in sandbox")
            test_result = self._validate_and_test_code(code)
            logger.debug(f"[SkillBuilder] Sandbox test result: success={test_result.get('success')}")
            
            if not test_result['success']:
                error_msg = f"Error: Generated skill failed validation:\n{test_result.get('error', 'Unknown error')}"
                logger.error(f"[SkillBuilder] Validation failed: {test_result.get('error')}")
                IOMsg.send_msg(error_msg)
                return error_msg
            
            logger.info("[SkillBuilder] Generated skill validated successfully")
            IOMsg.send_msg("✓ Generated skill validated successfully")
            
            # Get skills directory
            skills_dir = self._get_skills_directory()
            logger.debug(f"[SkillBuilder] Skills directory: {skills_dir}")
            
            # Save skill
            skill_file = generator.save_skill(code, skill_name, skills_dir)
            logger.info(f"[SkillBuilder] Skill saved to: {skill_file}")
            
            success_msg = f"✓ Skill '{skill_name}' created from prompt!\n"
            success_msg += f"File: {skill_file}\n"
            success_msg += "Note: This is a template. You may need to edit the implementation.\n"
            success_msg += "To use this skill, reload skills with the reload_skills command."
            
            IOMsg.send_msg(success_msg)
            return success_msg
            
        except Exception as e:
            logger.exception(f"[SkillBuilder] Error creating simple skill: {str(e)}")
            error_msg = f"Error creating simple skill: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg


# Example usage
if __name__ == "__main__":
    builder = SkillBuilder()
    
    # Example 1: Create a simple skill from prompt
    print("\n=== Example 1: Create simple skill ===")
    result = builder.create_simple_skill(
        skill_name="WeatherChecker",
        prompt="Check the weather in a specified city"
    )
    print(result)
    
    # Example 2: Generate a skill with specific parameters
    print("\n=== Example 2: Generate skill with parameters ===")
    import json
    params = json.dumps([
        {
            'name': 'city',
            'type': 'str',
            'description': 'City name to check weather'
        },
        {
            'name': 'units',
            'type': 'str',
            'description': 'Temperature units (celsius or fahrenheit)'
        }
    ])
    
    implementation = '''        # Example implementation
        result = f"Checking weather in {city} with {units} units"
        # TODO: Add actual API call here
        IOMsg.send_msg(result)
        return result'''
    
    result = builder.generate_skill(
        skill_name="WeatherAPI",
        description="Get weather information for a city",
        parameters=params,
        implementation=implementation
    )
    print(result)
