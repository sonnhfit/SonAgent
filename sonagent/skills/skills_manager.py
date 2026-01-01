import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel

from sonagent.skills.loading import BaseLoading
from sonagent.utils.utils import hash_md5_str

logger = logging.getLogger(__name__)

# Lazy import for sandbox to avoid Docker dependency when not needed
_sandbox_module = None

def _get_sandbox_module():
    """Lazy load sandbox module."""
    global _sandbox_module
    if _sandbox_module is None:
        try:
            from sonagent.sandbox import DockerSandbox, SandboxResult
            _sandbox_module = {
                'DockerSandbox': DockerSandbox,
                'SandboxResult': SandboxResult,
                'available': True
            }
        except ImportError as e:
            logger.warning(f"Docker sandbox not available: {e}")
            _sandbox_module = {'available': False}
    return _sandbox_module


class SkillsManager:
    """
    Manager for loading, testing, and managing skills.
    
    Supports testing skills in Docker sandbox before deployment.
    """

    def __init__(self, sonagent) -> None:
        self.skill_object_list: List[BaseModel] = []
        self.config = sonagent.config
        self.skills_area = "son_skills"
        self._sandbox = None
        self._sandbox_enabled = self.config.get('sandbox', {}).get('enabled', False)

    def load_register_skills_name(self) -> List[str]:
        skill_file_name = self.config.get('skills_file_path', 'skills.yaml')
        skill_file_path = Path(self.config['user_data_dir']).joinpath(skill_file_name)
        with open(skill_file_path, 'r') as file:
            skills_register = yaml.safe_load(file)

        if skills_register['skills'] is None:
            skills_register['skills'] = []
            
        return skills_register['skills']
    

    def load_skills(self) -> None:
        skills_register = self.load_register_skills_name()
        BaseLoading.object_type = BaseModel
        for skill_name in skills_register:
            skill = BaseLoading.load_object(object_name=skill_name, config=self.config, kwargs={}, extra_dir='user_data/skills')
            self.skill_object_list.append(skill)

    
    def reload_skills(self) -> None:
        self.skill_object_list = []
        self.load_skills()


    def get_all_skills(self) -> List[BaseModel]:
        return self.skill_object_list
    
    def search_skill_function_by_semantic_query(self, query: str, memory) -> List[BaseModel]:
        results = memory.search(
            collection_name=self.skills_area,
            query=query
        )
        return results
    
    def start_skill(self, memory: Any) -> None:
        # clear memory collection 
        try:
            memory.delete_memory_collection(self.skills_area)
        except Exception as e:
            logger.info(f"Error deleting memory collection: {e}")

        self.load_skills()
        self.save_skills_function_to_memory(memory=memory)
    
    def remove_skill_by_name(self, skill_name: str, memory: Any) -> None:
        # clear memory collection 
        try:
            memory.delete_memory_collection(self.skills_area)
        except Exception as e:
            logger.info(f"Error deleting memory collection: {e}")

        self.load_skills()
        self.skill_object_list = [skill for skill in self.skill_object_list if skill.__doc__ != skill_name]
        self.save_skills_function_to_memory(memory=memory)

    def save_skills_function_to_memory(self, memory: Any) -> None:
        logger.info("Adding skills to memory.")
        logger.info(f"Adding skills to memory. {self.skill_object_list}")
        for skill in self.skill_object_list:
            logger.info(f"Adding skill {str(skill.__doc__)} to memory: {hash_md5_str(skill.__doc__)}")
            is_added = memory.add(
                document=skill.__doc__,
                metadata={'skill_description': skill.__doc__},
                id=hash_md5_str(skill.__doc__),
                collection_name=self.skills_area
            )
            if is_added:
                logger.info(f"Skill {skill} added to memory.")
    
    def get_available_function_skills(self, query: str, memory: Any) -> List[BaseModel]:
        logger.info(f"Searching for skills that match the query {query}")

        # Search for functions that match the semantic query.
        function_list = self.search_skill_function_by_semantic_query(query=query, memory=memory)
        # logger.info(f"Found functions: {function_list}")
        # WriterSkill.Translate
        # description: translate the input to another language
        # args:
        # - input: the text to translate
        # - language: the language to translate to
        result = ""

        function_list_ids = function_list["ids"][0]
        function_list_metadatas = function_list["metadatas"][0]

        # logger.info(f"Found function_list_metadatas: {function_list_metadatas}")

        logger.info(f"Found function_list_ids: {function_list_ids}")

        for fun_docs in function_list_metadatas:
            # print(dir(fun_docs))
            result += fun_docs["skill_description"]

        # Add functions that were found in the search results.

        # Add any missing functions that were included but not found in the search results.
        logger.info(f"Found functions: {result}")

        return result

    # ==================== Sandbox Methods ====================
    
    @property
    def sandbox(self):
        """Get or create Docker sandbox instance."""
        if self._sandbox is None:
            sandbox_module = _get_sandbox_module()
            if sandbox_module.get('available'):
                sandbox_config = self.config.get('sandbox', {})
                from sonagent.sandbox.docker_sandbox import SandboxConfig
                config = SandboxConfig(
                    timeout=sandbox_config.get('timeout', 30),
                    memory_limit=sandbox_config.get('memory_limit', '256m'),
                    cpu_limit=sandbox_config.get('cpu_limit', 0.5),
                    network_disabled=sandbox_config.get('network_disabled', True)
                )
                self._sandbox = sandbox_module['DockerSandbox'](config)
            else:
                raise RuntimeError("Docker sandbox is not available. Install docker package.")
        return self._sandbox
    
    def is_sandbox_available(self) -> bool:
        """Check if Docker sandbox is available."""
        sandbox_module = _get_sandbox_module()
        if not sandbox_module.get('available'):
            return False
        try:
            return self.sandbox.is_docker_available()
        except Exception:
            return False
    
    def test_skill_in_sandbox(
        self,
        skill_name: str,
        method_name: Optional[str] = None,
        test_args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Test a skill in Docker sandbox before deployment.
        
        Args:
            skill_name: Name of the skill class to test
            method_name: Optional method name to test (if None, only validates syntax)
            test_args: Arguments to pass to the method
            
        Returns:
            Dict with test results:
                - success: bool
                - output: str
                - error: str
                - execution_time: float
        """
        if not self.is_sandbox_available():
            return {
                'success': False,
                'error': 'Docker sandbox is not available',
                'output': '',
                'execution_time': 0.0
            }
        
        # Find skill file
        skill_file_path = self._find_skill_file(skill_name)
        if not skill_file_path:
            return {
                'success': False,
                'error': f'Skill file not found for: {skill_name}',
                'output': '',
                'execution_time': 0.0
            }
        
        # Read skill code
        skill_code = skill_file_path.read_text()
        
        # Run test
        if method_name:
            result = self.sandbox.run_skill_with_args(
                skill_code=skill_code,
                class_name=skill_name,
                method_name=method_name,
                args=test_args or {}
            )
        else:
            result = self.sandbox.validate_skill_syntax(skill_code)
        
        return {
            'success': result.success,
            'output': result.output,
            'error': result.error,
            'execution_time': result.execution_time,
            'logs': result.logs
        }
    
    def test_skill_code_in_sandbox(
        self,
        skill_code: str,
        class_name: str,
        method_name: Optional[str] = None,
        test_args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Test skill code directly in Docker sandbox.
        
        Args:
            skill_code: Python code of the skill
            class_name: Name of the skill class
            method_name: Optional method name to test
            test_args: Arguments to pass to the method
            
        Returns:
            Dict with test results
        """
        if not self.is_sandbox_available():
            return {
                'success': False,
                'error': 'Docker sandbox is not available',
                'output': '',
                'execution_time': 0.0
            }
        
        if method_name:
            result = self.sandbox.run_skill_with_args(
                skill_code=skill_code,
                class_name=class_name,
                method_name=method_name,
                args=test_args or {}
            )
        else:
            result = self.sandbox.validate_skill_syntax(skill_code)
        
        return {
            'success': result.success,
            'output': result.output,
            'error': result.error,
            'execution_time': result.execution_time,
            'logs': result.logs
        }
    
    def _find_skill_file(self, skill_name: str) -> Optional[Path]:
        """Find the file containing a skill by name."""
        # Search in user_data/skills directory
        skills_dir = Path(self.config['user_data_dir']).joinpath('skills')
        
        if skills_dir.exists():
            for py_file in skills_dir.glob('*.py'):
                content = py_file.read_text()
                if f'class {skill_name}' in content:
                    return py_file
        
        return None
    
    def load_skill_with_sandbox_test(
        self,
        skill_name: str,
        test_method: Optional[str] = None,
        test_args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Load a skill after testing it in sandbox.
        
        Args:
            skill_name: Name of the skill to load
            test_method: Optional method to test before loading
            test_args: Arguments for the test method
            
        Returns:
            Dict with:
                - success: bool
                - skill: loaded skill object or None
                - test_result: sandbox test result
        """
        # Test in sandbox first
        test_result = self.test_skill_in_sandbox(
            skill_name=skill_name,
            method_name=test_method,
            test_args=test_args
        )
        
        if not test_result['success']:
            logger.warning(f"Skill {skill_name} failed sandbox test: {test_result['error']}")
            return {
                'success': False,
                'skill': None,
                'test_result': test_result
            }
        
        # Load skill if test passed
        try:
            BaseLoading.object_type = BaseModel
            skill = BaseLoading.load_object(
                object_name=skill_name,
                config=self.config,
                kwargs={},
                extra_dir='user_data/skills'
            )
            self.skill_object_list.append(skill)
            logger.info(f"Skill {skill_name} loaded successfully after sandbox test")
            return {
                'success': True,
                'skill': skill,
                'test_result': test_result
            }
        except Exception as e:
            logger.error(f"Failed to load skill {skill_name}: {e}")
            return {
                'success': False,
                'skill': None,
                'test_result': test_result,
                'load_error': str(e)
            }
    
    def cleanup_sandbox(self) -> None:
        """Clean up sandbox resources."""
        if self._sandbox:
            self._sandbox.cleanup()
            self._sandbox = None

