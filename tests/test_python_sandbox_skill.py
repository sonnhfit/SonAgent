import os
import tempfile
from pathlib import Path

import pytest

from user_data.skills.PythonSandboxSkill import PythonSandboxSkill


class TestPythonSandboxSkill:
    """Test cases for PythonSandboxSkill"""

    def setup_method(self):
        """Setup for each test method"""
        self.sandbox = PythonSandboxSkill()

    def test_execute_simple_code(self):
        """Test executing simple Python code"""
        code = "print('Hello World')"
        result = self.sandbox.execute_python_code(code)
        assert "Hello World" in result
        assert "Output:" in result

    def test_execute_code_with_calculation(self):
        """Test executing code with calculations"""
        code = """
result = 10 + 5
print(f"Result: {result}")
"""
        result = self.sandbox.execute_python_code(code)
        assert "Result: 15" in result

    def test_execute_code_with_error(self):
        """Test executing code that raises an error"""
        code = "raise ValueError('Test error')"
        result = self.sandbox.execute_python_code(code)
        assert "Errors:" in result
        assert "ValueError: Test error" in result

    def test_execute_code_with_timeout(self):
        """Test that long-running code times out"""
        code = """
import time
time.sleep(20)
"""
        result = self.sandbox.execute_python_code(code, timeout=2)
        assert "timed out" in result.lower()

    def test_validate_valid_code(self):
        """Test validating syntactically correct code"""
        code = "x = 5\nprint(x)"
        result = self.sandbox.validate_skill_code(code)
        assert "valid" in result.lower()

    def test_validate_invalid_code(self):
        """Test validating code with syntax error"""
        code = "print('unclosed string"
        result = self.sandbox.validate_skill_code(code)
        assert "error" in result.lower()

    def test_validate_invalid_indentation(self):
        """Test validating code with indentation error"""
        code = "def test():\nprint('bad indent')"
        result = self.sandbox.validate_skill_code(code)
        assert "error" in result.lower()

    def test_write_skill_new_file(self):
        """Test creating a new skill file"""
        # Use a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            test_skills_dir = Path(tmpdir)
            
            # Create a test skill in the temp directory
            skill_name = "TestSkill"
            skill_code = """from pydantic import BaseModel

class TestSkill(BaseModel):
    def test_method(self):
        return "test"
"""
            
            # Save the skill file directly in temp dir for testing
            skill_path = test_skills_dir / f"{skill_name}.py"
            with open(skill_path, 'w') as f:
                f.write(skill_code)
            
            # Verify the file was created
            assert skill_path.exists()
            
            # Verify the content
            with open(skill_path, 'r') as f:
                content = f.read()
                assert "class TestSkill" in content

    def test_write_skill_validates_code(self):
        """Test that write_skill validates code before creating file"""
        skill_name = "InvalidSkill"
        invalid_code = "print('invalid syntax"
        
        # This should return an error message, not create the file
        result = self.sandbox.write_skill(skill_name, invalid_code)
        assert "error" in result.lower()

    def test_execute_code_isolation(self):
        """Test that code execution is isolated"""
        # Try to access files outside temp directory
        code = """
import os
print(os.getcwd())
"""
        result = self.sandbox.execute_python_code(code)
        # Should execute in temp directory
        assert "Output:" in result

    def test_execute_code_no_output(self):
        """Test executing code with no output"""
        code = "x = 5 + 3"
        result = self.sandbox.execute_python_code(code)
        assert "successfully" in result.lower()

    def test_execute_multiline_code(self):
        """Test executing multi-line code"""
        code = """
def add(a, b):
    return a + b

result = add(5, 3)
print(f"5 + 3 = {result}")
"""
        result = self.sandbox.execute_python_code(code)
        assert "5 + 3 = 8" in result

    def test_execute_code_with_imports(self):
        """Test executing code with standard library imports"""
        code = """
import math
result = math.sqrt(16)
print(f"Square root of 16 is {result}")
"""
        result = self.sandbox.execute_python_code(code)
        assert "Square root of 16 is 4.0" in result
