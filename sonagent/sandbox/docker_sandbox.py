"""
Docker Sandbox for testing skills in isolated containers.
"""

import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result of running a skill in sandbox."""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    logs: str = ""


@dataclass
class SandboxConfig:
    """Configuration for Docker sandbox."""
    image: str = "python:3.11-slim"
    timeout: int = 30  # seconds
    memory_limit: str = "256m"
    cpu_limit: float = 0.5
    network_disabled: bool = True
    working_dir: str = "/sandbox"
    auto_remove: bool = True
    extra_packages: List[str] = field(default_factory=list)


class DockerSandbox:
    """
    Docker Sandbox for running skills in isolated containers.
    
    This class provides a secure environment to test skills before
    deploying them to the main agent.
    """
    
    SANDBOX_IMAGE_NAME = "sonagent-sandbox"
    SANDBOX_DOCKERFILE = '''
FROM python:3.11-slim

WORKDIR /sandbox

# Install basic dependencies
RUN pip install --no-cache-dir pydantic

CMD ["python"]
'''
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._client: Optional[docker.DockerClient] = None
        self._sandbox_image_built = False
    
    @property
    def client(self) -> docker.DockerClient:
        """Lazy initialization of Docker client."""
        if self._client is None:
            try:
                self._client = docker.from_env()
                self._client.ping()
            except Exception as e:
                logger.error(f"Failed to connect to Docker: {e}")
                raise RuntimeError(
                    "Docker is not available. Please ensure Docker is installed and running."
                ) from e
        return self._client
    
    def _ensure_sandbox_image(self) -> str:
        """Build or get the sandbox image."""
        if self._sandbox_image_built:
            return self.SANDBOX_IMAGE_NAME
        
        try:
            self.client.images.get(self.SANDBOX_IMAGE_NAME)
            self._sandbox_image_built = True
            logger.info(f"Using existing sandbox image: {self.SANDBOX_IMAGE_NAME}")
        except ImageNotFound:
            logger.info(f"Building sandbox image: {self.SANDBOX_IMAGE_NAME}")
            self._build_sandbox_image()
            self._sandbox_image_built = True
        
        return self.SANDBOX_IMAGE_NAME
    
    def _build_sandbox_image(self) -> None:
        """Build the sandbox Docker image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text(self.SANDBOX_DOCKERFILE)
            
            try:
                self.client.images.build(
                    path=tmpdir,
                    tag=self.SANDBOX_IMAGE_NAME,
                    rm=True,
                    forcerm=True
                )
                logger.info(f"Successfully built sandbox image: {self.SANDBOX_IMAGE_NAME}")
            except Exception as e:
                logger.error(f"Failed to build sandbox image: {e}")
                raise
    
    def _create_test_script(self, skill_code: str, test_code: str) -> str:
        """Create a test script that imports and tests the skill."""
        return f'''
import sys
import traceback

# Skill code
{skill_code}

# Test code
def run_test():
    try:
{self._indent_code(test_code, 8)}
        print("TEST_SUCCESS")
        return True
    except Exception as e:
        print(f"TEST_FAILED: {{e}}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
'''
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified number of spaces."""
        indent = " " * spaces
        lines = code.split("\n")
        return "\n".join(indent + line if line.strip() else line for line in lines)
    
    def run_skill_test(
        self,
        skill_code: str,
        test_code: str,
        skill_name: str = "TestSkill",
        extra_files: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """
        Run a skill test in the Docker sandbox.
        
        Args:
            skill_code: The Python code of the skill to test
            test_code: The test code to execute
            skill_name: Name of the skill (for logging)
            extra_files: Additional files to include in the sandbox
            
        Returns:
            SandboxResult with test results
        """
        start_time = time.time()
        
        try:
            image_name = self._ensure_sandbox_image()
        except Exception as e:
            return SandboxResult(
                success=False,
                error=f"Failed to prepare sandbox image: {e}",
                exit_code=-1
            )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write skill and test code
            test_script = self._create_test_script(skill_code, test_code)
            script_path = Path(tmpdir) / "test_skill.py"
            script_path.write_text(test_script)
            
            # Write extra files if provided
            if extra_files:
                for filename, content in extra_files.items():
                    file_path = Path(tmpdir) / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content)
            
            try:
                result = self._run_container(tmpdir, image_name, skill_name)
                result.execution_time = time.time() - start_time
                return result
            except Exception as e:
                return SandboxResult(
                    success=False,
                    error=str(e),
                    exit_code=-1,
                    execution_time=time.time() - start_time
                )
    
    def _run_container(
        self,
        work_dir: str,
        image_name: str,
        skill_name: str
    ) -> SandboxResult:
        """Run the test container and collect results."""
        container = None
        
        try:
            container = self.client.containers.run(
                image=image_name,
                command=["python", "/sandbox/test_skill.py"],
                volumes={
                    work_dir: {"bind": "/sandbox", "mode": "ro"}
                },
                working_dir="/sandbox",
                mem_limit=self.config.memory_limit,
                cpu_period=100000,
                cpu_quota=int(100000 * self.config.cpu_limit),
                network_disabled=self.config.network_disabled,
                detach=True,
                remove=False,  # We'll remove manually after getting logs
            )
            
            # Wait for container to finish
            exit_result = container.wait(timeout=self.config.timeout)
            exit_code = exit_result.get("StatusCode", -1)
            
            # Get logs
            logs = container.logs(stdout=True, stderr=True).decode("utf-8")
            
            # Parse results
            success = "TEST_SUCCESS" in logs and exit_code == 0
            
            # Extract output and error
            output_lines = []
            error_lines = []
            for line in logs.split("\n"):
                if "TEST_FAILED:" in line or "Traceback" in line or "Error" in line:
                    error_lines.append(line)
                else:
                    output_lines.append(line)
            
            return SandboxResult(
                success=success,
                output="\n".join(output_lines).strip(),
                error="\n".join(error_lines).strip(),
                exit_code=exit_code,
                logs=logs
            )
            
        except ContainerError as e:
            return SandboxResult(
                success=False,
                error=f"Container error: {e}",
                exit_code=e.exit_status,
                logs=e.stderr.decode("utf-8") if e.stderr else ""
            )
        except Exception as e:
            logger.error(f"Error running sandbox container: {e}")
            return SandboxResult(
                success=False,
                error=str(e),
                exit_code=-1
            )
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
    
    def validate_skill_syntax(self, skill_code: str) -> SandboxResult:
        """
        Validate skill code syntax without executing it.
        
        Args:
            skill_code: The Python code to validate
            
        Returns:
            SandboxResult indicating if syntax is valid
        """
        # Escape the skill code for embedding in test script
        escaped_code = skill_code.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
        
        test_code = f'''
import ast
skill_code = '{escaped_code}'
skill_code = skill_code.replace('\\\\n', '\\n')
try:
    ast.parse(skill_code)
    print("Syntax is valid")
except SyntaxError as e:
    raise Exception(f"Syntax error: {{e}}")
'''
        return self.run_skill_test(
            skill_code="",
            test_code=test_code,
            skill_name="SyntaxValidation"
        )
    
    def run_skill_with_args(
        self,
        skill_code: str,
        class_name: str,
        method_name: str,
        args: Optional[Dict[str, Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> SandboxResult:
        """
        Run a specific skill method with arguments in the sandbox.
        
        Args:
            skill_code: The Python code of the skill
            class_name: Name of the skill class
            method_name: Name of the method to call
            args: Positional arguments as dict (will be passed as **kwargs)
            kwargs: Keyword arguments
            
        Returns:
            SandboxResult with execution results
        """
        args = args or {}
        kwargs = kwargs or {}
        all_kwargs = {**args, **kwargs}
        
        # Build the test code
        kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in all_kwargs.items())
        
        test_code = f'''
skill = {class_name}()
result = skill.{method_name}({kwargs_str})
print(f"Result: {{result}}")
'''
        return self.run_skill_test(
            skill_code=skill_code,
            test_code=test_code,
            skill_name=f"{class_name}.{method_name}"
        )
    
    def cleanup(self) -> None:
        """Clean up Docker resources."""
        if self._client:
            try:
                # Remove sandbox image if exists
                try:
                    self._client.images.remove(self.SANDBOX_IMAGE_NAME, force=True)
                    logger.info(f"Removed sandbox image: {self.SANDBOX_IMAGE_NAME}")
                except ImageNotFound:
                    pass
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
            finally:
                self._client.close()
                self._client = None
                self._sandbox_image_built = False
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False


class SkillSandboxTester:
    """
    High-level interface for testing skills in sandbox.
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.sandbox = DockerSandbox(config)
    
    def test_skill_file(
        self,
        skill_file_path: str,
        test_cases: Optional[List[Dict[str, Any]]] = None
    ) -> List[SandboxResult]:
        """
        Test a skill from a file.
        
        Args:
            skill_file_path: Path to the skill Python file
            test_cases: List of test cases, each containing:
                - class_name: Name of the skill class
                - method_name: Method to test
                - args: Arguments to pass
                - expected: Expected result (optional)
                
        Returns:
            List of SandboxResult for each test case
        """
        skill_path = Path(skill_file_path)
        if not skill_path.exists():
            return [SandboxResult(
                success=False,
                error=f"Skill file not found: {skill_file_path}"
            )]
        
        skill_code = skill_path.read_text()
        results = []
        
        # First validate syntax
        syntax_result = self.sandbox.validate_skill_syntax(skill_code)
        if not syntax_result.success:
            return [syntax_result]
        
        # Run test cases
        if test_cases:
            for test_case in test_cases:
                result = self.sandbox.run_skill_with_args(
                    skill_code=skill_code,
                    class_name=test_case.get("class_name", ""),
                    method_name=test_case.get("method_name", ""),
                    args=test_case.get("args", {}),
                    kwargs=test_case.get("kwargs", {})
                )
                results.append(result)
        else:
            # Just validate syntax if no test cases
            results.append(syntax_result)
        
        return results
    
    def quick_test(
        self,
        skill_code: str,
        class_name: str,
        method_name: str,
        **kwargs
    ) -> SandboxResult:
        """
        Quick test a skill method.
        
        Args:
            skill_code: The skill code
            class_name: Class name
            method_name: Method name
            **kwargs: Arguments to pass to the method
            
        Returns:
            SandboxResult
        """
        return self.sandbox.run_skill_with_args(
            skill_code=skill_code,
            class_name=class_name,
            method_name=method_name,
            kwargs=kwargs
        )
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.sandbox.cleanup()
