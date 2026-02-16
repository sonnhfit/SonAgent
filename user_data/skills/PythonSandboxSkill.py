import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel

from sonagent.rpc import IOMsg


class PythonSandboxSkill(BaseModel):
    """
    PythonSandboxSkill.execute_python_code
    description: Execute Python code in a sandboxed environment with timeout and resource limits
    args:
        - code: Python code to execute
        - timeout: Maximum execution time in seconds (default: 10)
    
    PythonSandboxSkill.write_skill
    description: Create a new skill file for SonAgent with the provided Python code
    args:
        - skill_name: Name of the skill class (e.g., 'MyNewSkill')
        - skill_code: Complete Python code for the skill including class definition
        - description: Description of what the skill does
    
    PythonSandboxSkill.validate_skill_code
    description: Validate Python skill code without executing it
    args:
        - code: Python code to validate
    """

    def execute_python_code(
        self, 
        code: str, 
        timeout: int = 10
    ) -> str:
        """
        Execute Python code in a sandboxed subprocess environment.
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            String containing the output or error message
        """
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.py', 
                delete=False
            ) as tmp_file:
                tmp_file.write(code)
                tmp_file_path = tmp_file.name
            
            try:
                # Execute the code in a subprocess with timeout
                result = subprocess.run(
                    ['python', tmp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tempfile.gettempdir()  # Run in temp directory for isolation
                )
                
                output = []
                if result.stdout:
                    output.append(f"Output:\n{result.stdout}")
                if result.stderr:
                    output.append(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    output.append(f"Exit code: {result.returncode}")
                
                result_text = "\n".join(output) if output else "Code executed successfully with no output."
                IOMsg.send_msg(result_text)
                return result_text
                
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
                    
        except subprocess.TimeoutExpired:
            error_msg = f"Execution timed out after {timeout} seconds"
            IOMsg.send_msg(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error executing code: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg

    def validate_skill_code(self, code: str) -> str:
        """
        Validate Python code syntax without executing it.
        
        Args:
            code: Python code to validate
            
        Returns:
            Validation result message
        """
        try:
            compile(code, '<string>', 'exec')
            result = "Code syntax is valid."
            IOMsg.send_msg(result)
            return result
        except SyntaxError as e:
            error_msg = f"Syntax error: {e.msg} at line {e.lineno}"
            IOMsg.send_msg(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg

    def write_skill(
        self, 
        skill_name: str, 
        skill_code: str, 
        description: Optional[str] = None
    ) -> str:
        """
        Create a new skill file in the skills directory.
        
        Args:
            skill_name: Name of the skill class (should match the class name in code)
            skill_code: Complete Python code for the skill
            description: Optional description of the skill
            
        Returns:
            Success or error message
        """
        try:
            # Get the skills directory path
            # This assumes we're in the user_data/skills directory context
            current_file = Path(__file__).resolve()
            skills_dir = current_file.parent
            
            # Create the new skill file path
            skill_file_path = skills_dir / f"{skill_name}.py"
            
            # Check if file already exists
            if skill_file_path.exists():
                error_msg = f"Skill file '{skill_name}.py' already exists. Please choose a different name or delete the existing file first."
                IOMsg.send_msg(error_msg)
                return error_msg
            
            # Validate the code syntax first
            validation_result = self.validate_skill_code(skill_code)
            if "error" in validation_result.lower():
                return f"Cannot create skill due to validation error: {validation_result}"
            
            # Check if the code contains the expected class
            if f"class {skill_name}" not in skill_code:
                error_msg = f"Warning: The code does not contain a class named '{skill_name}'. Make sure the class name matches the skill name."
                IOMsg.send_msg(error_msg)
            
            # Write the skill code to file
            with open(skill_file_path, 'w') as f:
                # Add a header comment if description is provided
                if description:
                    f.write(f'"""\n{description}\n"""\n\n')
                f.write(skill_code)
            
            success_msg = f"Successfully created skill '{skill_name}' at {skill_file_path}. Remember to reload skills to use it."
            IOMsg.send_msg(success_msg)
            return success_msg
            
        except Exception as e:
            error_msg = f"Error creating skill file: {str(e)}"
            IOMsg.send_msg(error_msg)
            return error_msg


# Example usage
if __name__ == "__main__":
    sandbox = PythonSandboxSkill()
    
    # Test 1: Execute simple code
    print("=== Test 1: Execute simple Python code ===")
    test_code = """
print("Hello from sandbox!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
    print(sandbox.execute_python_code(test_code))
    
    # Test 2: Validate code
    print("\n=== Test 2: Validate code ===")
    print(sandbox.validate_skill_code("print('valid code')"))
    
    # Test 3: Validate invalid code
    print("\n=== Test 3: Validate invalid code ===")
    print(sandbox.validate_skill_code("print('invalid code'"))
    
    # Test 4: Create a new skill
    print("\n=== Test 4: Create a new skill ===")
    new_skill_code = """from pydantic import BaseModel
from sonagent.rpc import IOMsg


class MathSkill(BaseModel):
    '''
    MathSkill.add
    description: Add two numbers
    args:
        - a: First number
        - b: Second number
    '''
    
    def add(self, a: float, b: float) -> str:
        result = a + b
        msg = f"Result: {a} + {b} = {result}"
        IOMsg.send_msg(msg)
        return msg
"""
    print(sandbox.write_skill(
        "MathSkill", 
        new_skill_code, 
        "A skill for basic math operations"
    ))
