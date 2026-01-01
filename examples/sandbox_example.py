"""
Example: Testing skills in Docker Sandbox

This example demonstrates how to use the Docker Sandbox to test skills
before deploying them to the main agent.
"""

from sonagent.sandbox import DockerSandbox, SandboxResult
from sonagent.sandbox.docker_sandbox import SandboxConfig, SkillSandboxTester


def example_basic_sandbox():
    """Basic example of using Docker Sandbox."""
    print("=" * 50)
    print("Example 1: Basic Sandbox Usage")
    print("=" * 50)
    
    # Create sandbox with default config
    sandbox = DockerSandbox()
    
    # Check if Docker is available
    if not sandbox.is_docker_available():
        print("Docker is not available. Please install and start Docker.")
        return
    
    # Define a simple skill
    skill_code = '''
from pydantic import BaseModel

class Calculator(BaseModel):
    """
    Calculator.add
    description: Add two numbers
    args:
        - a: first number
        - b: second number
    """
    
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def multiply(self, a: int, b: int) -> int:
        return a * b
'''
    
    # Test the skill
    print("\nTesting Calculator.add(2, 3)...")
    result = sandbox.run_skill_with_args(
        skill_code=skill_code,
        class_name="Calculator",
        method_name="add",
        args={"a": 2, "b": 3}
    )
    
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    print(f"Execution time: {result.execution_time:.2f}s")
    
    if result.error:
        print(f"Error: {result.error}")
    
    # Cleanup
    sandbox.cleanup()


def example_syntax_validation():
    """Example of validating skill syntax."""
    print("\n" + "=" * 50)
    print("Example 2: Syntax Validation")
    print("=" * 50)
    
    sandbox = DockerSandbox()
    
    if not sandbox.is_docker_available():
        print("Docker is not available.")
        return
    
    # Valid syntax
    valid_code = '''
class ValidSkill:
    def method(self):
        return "valid"
'''
    
    print("\nValidating valid code...")
    result = sandbox.validate_skill_syntax(valid_code)
    print(f"Valid code - Success: {result.success}")
    
    # Invalid syntax
    invalid_code = '''
class InvalidSkill
    def method(self):
        return "invalid"
'''
    
    print("\nValidating invalid code...")
    result = sandbox.validate_skill_syntax(invalid_code)
    print(f"Invalid code - Success: {result.success}")
    if result.error:
        print(f"Error: {result.error}")
    
    sandbox.cleanup()


def example_custom_config():
    """Example with custom sandbox configuration."""
    print("\n" + "=" * 50)
    print("Example 3: Custom Configuration")
    print("=" * 50)
    
    # Create custom config
    config = SandboxConfig(
        timeout=60,           # 60 seconds timeout
        memory_limit="512m",  # 512MB memory limit
        cpu_limit=1.0,        # Full CPU core
        network_disabled=True # No network access
    )
    
    sandbox = DockerSandbox(config)
    
    if not sandbox.is_docker_available():
        print("Docker is not available.")
        return
    
    print(f"Timeout: {config.timeout}s")
    print(f"Memory limit: {config.memory_limit}")
    print(f"CPU limit: {config.cpu_limit}")
    print(f"Network disabled: {config.network_disabled}")
    
    # Test a skill with custom config
    skill_code = '''
from pydantic import BaseModel

class StringProcessor(BaseModel):
    def reverse(self, text: str) -> str:
        return text[::-1]
'''
    
    result = sandbox.run_skill_with_args(
        skill_code=skill_code,
        class_name="StringProcessor",
        method_name="reverse",
        args={"text": "Hello World"}
    )
    
    print(f"\nResult: {result.output}")
    print(f"Success: {result.success}")
    
    sandbox.cleanup()


def example_skill_tester():
    """Example using SkillSandboxTester for high-level testing."""
    print("\n" + "=" * 50)
    print("Example 4: Using SkillSandboxTester")
    print("=" * 50)
    
    tester = SkillSandboxTester()
    
    if not tester.sandbox.is_docker_available():
        print("Docker is not available.")
        return
    
    # Quick test a skill
    skill_code = '''
from pydantic import BaseModel

class Greeter(BaseModel):
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"
'''
    
    print("\nQuick testing Greeter.greet('World')...")
    result = tester.quick_test(
        skill_code=skill_code,
        class_name="Greeter",
        method_name="greet",
        name="World"
    )
    
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    
    tester.cleanup()


def example_error_handling():
    """Example of handling errors in sandbox."""
    print("\n" + "=" * 50)
    print("Example 5: Error Handling")
    print("=" * 50)
    
    sandbox = DockerSandbox()
    
    if not sandbox.is_docker_available():
        print("Docker is not available.")
        return
    
    # Skill with runtime error
    skill_code = '''
from pydantic import BaseModel

class BuggySkill(BaseModel):
    def divide(self, a: int, b: int) -> float:
        return a / b  # Will raise ZeroDivisionError if b=0
'''
    
    print("\nTesting BuggySkill.divide(10, 0)...")
    result = sandbox.run_skill_with_args(
        skill_code=skill_code,
        class_name="BuggySkill",
        method_name="divide",
        args={"a": 10, "b": 0}
    )
    
    print(f"Success: {result.success}")
    print(f"Exit code: {result.exit_code}")
    if result.error:
        print(f"Error: {result.error}")
    
    sandbox.cleanup()


if __name__ == "__main__":
    print("Docker Sandbox Examples")
    print("=" * 50)
    
    try:
        example_basic_sandbox()
        example_syntax_validation()
        example_custom_config()
        example_skill_tester()
        example_error_handling()
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure Docker is installed and running.")
    
    print("\n" + "=" * 50)
    print("Examples completed!")
