"""
Skill Generator for creating new skills dynamically.
Generates Python code for skills following the SonAgent skill template.
"""
import logging
import re
from pathlib import Path
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class SkillGenerator:
    """Generate skill code from descriptions and specifications."""
    
    SKILL_TEMPLATE = '''from pydantic import BaseModel

from sonagent.rpc import IOMsg


class {class_name}(BaseModel):
    """
    {class_name}.{method_name}
    description: {description}
    args:
{args_section}
    """

    def {method_name}(self{method_params}):
        """{method_description_for_tool}
        
        Args:
{args_docs}
        
        Returns:
            {return_description}
        """
{method_implementation}

# Example usage
if __name__ == "__main__":
    skill = {class_name}()
    result = skill.{method_name}({example_call})
    print(result)
'''
    
    def __init__(self):
        """Initialize skill generator."""
        self.template = self.SKILL_TEMPLATE
    
    def generate_skill(
        self,
        skill_name: str,
        description: str,
        method_name: Optional[str] = None,
        parameters: Optional[List[Dict[str, str]]] = None,
        implementation: Optional[str] = None,
        return_description: str = "Result of the operation"
    ) -> str:
        """
        Generate skill code from specification.
        
        Args:
            skill_name: Name of the skill class (e.g., "WeatherChecker")
            description: Description of what the skill does
            method_name: Name of the main method (defaults to snake_case of skill_name)
            parameters: List of parameter dicts with 'name', 'type', and 'description'
            implementation: Python code for the method implementation
            return_description: Description of what the method returns
            
        Returns:
            Generated skill code as a string
        """
        # Validate skill name
        if not self._is_valid_class_name(skill_name):
            raise ValueError(f"Invalid skill name: {skill_name}. Must be a valid Python class name.")
        
        # Generate method name if not provided
        if not method_name:
            method_name = self._class_to_snake_case(skill_name)
        
        # Validate method name
        if not self._is_valid_method_name(method_name):
            raise ValueError(f"Invalid method name: {method_name}. Must be a valid Python method name.")
        
        # Process parameters
        if parameters is None:
            parameters = []
        
        # Generate method signature
        method_params = self._generate_method_params(parameters)
        
        # Generate args section for docstring
        args_section = self._generate_args_section(parameters)
        
        # Generate args documentation
        args_docs = self._generate_args_docs(parameters)
        
        # Generate method description for tool (short description for LangChain)
        method_description_for_tool = self._generate_method_description_for_tool(description, parameters)
        
        # Generate implementation
        if implementation is None:
            implementation = self._generate_default_implementation(parameters)
        else:
            # Ensure implementation is properly indented
            implementation = self._indent_code(implementation, 8)
        
        # Generate example call
        example_call = self._generate_example_call(parameters)
        
        # Fill template
        code = self.template.format(
            class_name=skill_name,
            method_name=method_name,
            description=description,
            args_section=args_section,
            method_params=method_params,
            method_description_for_tool=method_description_for_tool,
            args_docs=args_docs,
            return_description=return_description,
            method_implementation=implementation,
            example_call=example_call
        )
        
        return code
    
    def _is_valid_class_name(self, name: str) -> bool:
        """Check if name is a valid Python class name."""
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))
    
    def _is_valid_method_name(self, name: str) -> bool:
        """Check if name is a valid Python method name."""
        return bool(re.match(r'^[a-z_][a-z0-9_]*$', name))
    
    def _class_to_snake_case(self, class_name: str) -> str:
        """Convert CamelCase to snake_case."""
        # Insert underscore before uppercase letters (except first)
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        # Insert underscore before uppercase letters preceded by lowercase
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _generate_method_params(self, parameters: List[Dict[str, str]]) -> str:
        """Generate method parameter string."""
        if not parameters:
            return ""
        
        params = []
        for param in parameters:
            param_name = param['name']
            param_type = param.get('type', 'str')
            
            # Add type hint if provided
            if param_type:
                params.append(f"{param_name}: {param_type}")
            else:
                params.append(param_name)
        
        return ", " + ", ".join(params)
    
    def _generate_args_section(self, parameters: List[Dict[str, str]]) -> str:
        """Generate args section for class docstring."""
        if not parameters:
            return "        - None"
        
        args_lines = []
        for param in parameters:
            param_name = param['name']
            param_desc = param.get('description', 'parameter description')
            args_lines.append(f"        - {param_name}: {param_desc}")
        
        return "\n".join(args_lines)
    
    def _generate_args_docs(self, parameters: List[Dict[str, str]]) -> str:
        """Generate args documentation for method docstring."""
        if not parameters:
            return "            None"
        
        docs_lines = []
        for param in parameters:
            param_name = param['name']
            param_type = param.get('type', 'str')
            param_desc = param.get('description', 'parameter description')
            docs_lines.append(f"            {param_name} ({param_type}): {param_desc}")
        
        return "\n".join(docs_lines)
    
    def _generate_method_description_for_tool(self, description: str, parameters: List[Dict[str, str]]) -> str:
        """
        Generate a short description for LangChain tool.
        
        Creates a description that includes the skill's purpose and its parameters
        in a format that LangChain can use effectively.
        
        Args:
            description: The skill description
            parameters: List of parameter dicts
            
        Returns:
            Short description suitable for LangChain tool
        """
        # Start with the description
        desc = description.strip()
        
        # If there are parameters, add them to the description
        if parameters:
            param_list = []
            for param in parameters:
                param_name = param['name']
                param_type = param.get('type', 'str')
                param_desc = param.get('description', '')
                if param_desc:
                    param_list.append(f"{param_name} ({param_type}): {param_desc}")
                else:
                    param_list.append(f"{param_name} ({param_type})")
            
            if param_list:
                params_str = ", ".join(param_list)
                desc = f"{desc}. Args: {params_str}"
        
        return desc
    
    def _generate_default_implementation(self, parameters: List[Dict[str, str]]) -> str:
        """Generate a default implementation that returns parameter summary."""
        if not parameters:
            impl = '''result = "Skill executed successfully"
IOMsg.send_msg(result)
return result'''
        else:
            param_names = [p['name'] for p in parameters]
            params_str = ", ".join([f"{name}={{{name}}}" for name in param_names])
            impl = f'''result = f"Executed with parameters: {params_str}"
IOMsg.send_msg(result)
return result'''
        
        # Indent the implementation
        return self._indent_code(impl, 8)
    
    def _indent_code(self, code: str, indent_level: int) -> str:
        """Indent code by specified number of spaces."""
        indent = " " * indent_level
        lines = code.split('\n')
        return '\n'.join([indent + line if line.strip() else '' for line in lines])
    
    def _generate_example_call(self, parameters: List[Dict[str, str]]) -> str:
        """Generate example method call."""
        if not parameters:
            return ""
        
        example_args = []
        for param in parameters:
            param_name = param['name']
            param_type = param.get('type', 'str')
            
            # Generate example value based on type
            if param_type == 'str':
                example_value = f'"{param_name}_value"'
            elif param_type == 'int':
                example_value = '1'
            elif param_type == 'float':
                example_value = '1.0'
            elif param_type == 'bool':
                example_value = 'True'
            else:
                example_value = f'"{param_name}_value"'
            
            example_args.append(f'{param_name}={example_value}')
        
        return ", ".join(example_args)
    
    def save_skill(self, code: str, skill_name: str, skills_dir: Path) -> Path:
        """
        Save generated skill code to file.
        
        Args:
            code: Generated skill code
            skill_name: Name of the skill
            skills_dir: Directory to save the skill
            
        Returns:
            Path to saved skill file
        """
        # Ensure skills directory exists
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        # Create skill file path
        skill_file = skills_dir / f"{skill_name}.py"
        
        # Save code
        skill_file.write_text(code)
        logger.info(f"Saved skill to {skill_file}")
        
        return skill_file
    
    def generate_simple_skill_from_prompt(
        self,
        prompt: str,
        skill_name: str
    ) -> str:
        """
        Generate a simple skill from a natural language prompt.
        This is a basic implementation that could be enhanced with LLM integration.
        
        Args:
            prompt: Natural language description of what the skill should do
            skill_name: Name for the skill
            
        Returns:
            Generated skill code
        """
        # For now, create a simple skill that returns the prompt
        # This can be enhanced with LLM integration to generate proper implementation
        
        method_name = self._class_to_snake_case(skill_name)
        
        parameters = [
            {
                'name': 'input_text',
                'type': 'str',
                'description': 'Input text for the operation'
            }
        ]
        
        implementation = f'''# TODO: Implement actual logic for: {prompt}
result = f"Processing: {{input_text}}"
IOMsg.send_msg(result)
return result'''
        
        return self.generate_skill(
            skill_name=skill_name,
            description=prompt,
            method_name=method_name,
            parameters=parameters,
            implementation=implementation,
            return_description="Result of the operation"
        )
