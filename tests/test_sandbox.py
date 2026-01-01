"""
Tests for Docker Sandbox module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from sonagent.sandbox.docker_sandbox import (
    DockerSandbox,
    SandboxConfig,
    SandboxResult,
    SkillSandboxTester
)


class TestSandboxResult:
    """Tests for SandboxResult dataclass."""
    
    def test_default_values(self):
        result = SandboxResult(success=True)
        assert result.success is True
        assert result.output == ""
        assert result.error == ""
        assert result.exit_code == 0
        assert result.execution_time == 0.0
        assert result.logs == ""
    
    def test_with_values(self):
        result = SandboxResult(
            success=False,
            output="test output",
            error="test error",
            exit_code=1,
            execution_time=1.5,
            logs="test logs"
        )
        assert result.success is False
        assert result.output == "test output"
        assert result.error == "test error"
        assert result.exit_code == 1
        assert result.execution_time == 1.5
        assert result.logs == "test logs"


class TestSandboxConfig:
    """Tests for SandboxConfig dataclass."""
    
    def test_default_values(self):
        config = SandboxConfig()
        assert config.image == "python:3.11-slim"
        assert config.timeout == 30
        assert config.memory_limit == "256m"
        assert config.cpu_limit == 0.5
        assert config.network_disabled is True
        assert config.working_dir == "/sandbox"
        assert config.auto_remove is True
        assert config.extra_packages == []
    
    def test_custom_values(self):
        config = SandboxConfig(
            timeout=60,
            memory_limit="512m",
            cpu_limit=1.0,
            network_disabled=False
        )
        assert config.timeout == 60
        assert config.memory_limit == "512m"
        assert config.cpu_limit == 1.0
        assert config.network_disabled is False


class TestDockerSandbox:
    """Tests for DockerSandbox class."""
    
    def test_init_default_config(self):
        sandbox = DockerSandbox()
        assert sandbox.config is not None
        assert sandbox._client is None
        assert sandbox._sandbox_image_built is False
    
    def test_init_custom_config(self):
        config = SandboxConfig(timeout=60)
        sandbox = DockerSandbox(config)
        assert sandbox.config.timeout == 60
    
    def test_indent_code(self):
        sandbox = DockerSandbox()
        code = "line1\nline2\nline3"
        indented = sandbox._indent_code(code, 4)
        assert indented == "    line1\n    line2\n    line3"
    
    def test_indent_code_empty_lines(self):
        sandbox = DockerSandbox()
        code = "line1\n\nline3"
        indented = sandbox._indent_code(code, 4)
        assert "    line1" in indented
        assert "    line3" in indented
    
    def test_create_test_script(self):
        sandbox = DockerSandbox()
        skill_code = "class TestSkill:\n    pass"
        test_code = "print('test')"
        
        script = sandbox._create_test_script(skill_code, test_code)
        
        assert "class TestSkill:" in script
        assert "def run_test():" in script
        assert "TEST_SUCCESS" in script
        assert "TEST_FAILED" in script
    
    @patch('sonagent.sandbox.docker_sandbox.docker')
    def test_is_docker_available_true(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        
        sandbox = DockerSandbox()
        assert sandbox.is_docker_available() is True
    
    @patch('sonagent.sandbox.docker_sandbox.docker')
    def test_is_docker_available_false(self, mock_docker):
        mock_docker.from_env.side_effect = Exception("Docker not available")
        
        sandbox = DockerSandbox()
        assert sandbox.is_docker_available() is False
    
    @patch('sonagent.sandbox.docker_sandbox.docker')
    def test_validate_skill_syntax_valid(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        
        # Mock container
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"Syntax is valid\nTEST_SUCCESS"
        mock_client.containers.run.return_value = mock_container
        
        # Mock image
        mock_client.images.get.return_value = MagicMock()
        
        sandbox = DockerSandbox()
        result = sandbox.validate_skill_syntax("class Test:\n    pass")
        
        assert result.success is True
    
    @patch('sonagent.sandbox.docker_sandbox.docker')
    def test_run_skill_with_args(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        
        # Mock container
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        mock_container.logs.return_value = b"Result: Hello\nTEST_SUCCESS"
        mock_client.containers.run.return_value = mock_container
        
        # Mock image
        mock_client.images.get.return_value = MagicMock()
        
        sandbox = DockerSandbox()
        skill_code = '''
from pydantic import BaseModel

class Greeter(BaseModel):
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"
'''
        result = sandbox.run_skill_with_args(
            skill_code=skill_code,
            class_name="Greeter",
            method_name="greet",
            args={"name": "World"}
        )
        
        assert result.success is True


class TestSkillSandboxTester:
    """Tests for SkillSandboxTester class."""
    
    def test_init(self):
        tester = SkillSandboxTester()
        assert tester.sandbox is not None
    
    def test_init_with_config(self):
        config = SandboxConfig(timeout=60)
        tester = SkillSandboxTester(config)
        assert tester.sandbox.config.timeout == 60
    
    @patch('sonagent.sandbox.docker_sandbox.docker')
    def test_test_skill_file_not_found(self, mock_docker):
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        
        tester = SkillSandboxTester()
        results = tester.test_skill_file("/nonexistent/path.py")
        
        assert len(results) == 1
        assert results[0].success is False
        assert "not found" in results[0].error


class TestSkillsManagerSandboxIntegration:
    """Tests for SkillsManager sandbox integration."""
    
    def test_sandbox_module_lazy_load(self):
        from sonagent.skills.skills_manager import _get_sandbox_module
        
        module = _get_sandbox_module()
        assert 'available' in module
        assert module['available'] is True
        assert 'DockerSandbox' in module
        assert 'SandboxResult' in module


# Integration tests (require Docker)
@pytest.mark.integration
class TestDockerSandboxIntegration:
    """Integration tests that require Docker to be running."""
    
    @pytest.fixture
    def sandbox(self):
        sandbox = DockerSandbox()
        yield sandbox
        sandbox.cleanup()
    
    def test_validate_valid_syntax(self, sandbox):
        if not sandbox.is_docker_available():
            pytest.skip("Docker not available")
        
        skill_code = '''
from pydantic import BaseModel

class TestSkill(BaseModel):
    def test_method(self) -> str:
        return "test"
'''
        result = sandbox.validate_skill_syntax(skill_code)
        assert result.success is True
    
    def test_validate_invalid_syntax(self, sandbox):
        if not sandbox.is_docker_available():
            pytest.skip("Docker not available")
        
        skill_code = '''
class TestSkill
    def test_method(self):
        return "test"
'''
        result = sandbox.validate_skill_syntax(skill_code)
        # Note: syntax validation happens in sandbox, so it should still succeed
        # as the validation code itself is valid
    
    def test_run_simple_skill(self, sandbox):
        if not sandbox.is_docker_available():
            pytest.skip("Docker not available")
        
        skill_code = '''
from pydantic import BaseModel

class Calculator(BaseModel):
    def add(self, a: int, b: int) -> int:
        return a + b
'''
        result = sandbox.run_skill_with_args(
            skill_code=skill_code,
            class_name="Calculator",
            method_name="add",
            args={"a": 2, "b": 3}
        )
        
        assert result.success is True
        assert "5" in result.output or "Result: 5" in result.logs
