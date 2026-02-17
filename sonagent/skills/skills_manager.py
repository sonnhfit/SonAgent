import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from sonagent.skills.loading import BaseLoading
from sonagent.utils.utils import hash_md5_str

logger = logging.getLogger(__name__)


class SkillsManager:

    # load, and get skills from config

    def __init__(self, sonagent, agent_id: Optional[str] = None) -> None:
        self.skill_object_list: List[BaseModel] = []
        self.llm_skills: Dict[str, str] = {}  # markdown/LLM skills
        self.config = sonagent.config
        self.skills_area = "son_skills"
        self.agent_id = agent_id  # Agent ID for loading agent-specific skills
        
        # Set skills directory based on agent_id
        if agent_id:
            # Agent-specific skills directory: user_data/skills/{agent_id}/
            self.skills_dir = Path(self.config['user_data_dir']).joinpath('skills', agent_id)
        else:
            # Shared skills directory: user_data/skills/
            self.skills_dir = Path(self.config['user_data_dir']).joinpath('skills')
        
        self.last_scan_time = 0
        self.cached_skill_files = set()
        self.scan_interval = 60  # Scan every 60 seconds
        
        # Copy standard skills if user_data/skills is empty
        self.copy_standard_skills_if_needed()

    def copy_standard_skills_if_needed(self) -> None:
        """Copy standard skills to user_data/skills, overwriting if already exists."""
        # Ensure the skills directory exists
        if not self.skills_dir.exists():
            try:
                self.skills_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created skills directory: {self.skills_dir}")
            except Exception as e:
                logger.error(f"Failed to create skills directory {self.skills_dir}: {e}")
                return
        
        # Check if skills directory already has files
        skill_files = list(self.skills_dir.rglob('*'))
        if skill_files:
            logger.info(f"Skills directory already has {len(skill_files)} files. Emptying it first...")
            # Empty the skills directory
            for item in self.skills_dir.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                        logger.info(f"Removed file: {item}")
                    except Exception as e:
                        logger.error(f"Failed to remove file {item}: {e}")
                elif item.is_dir():
                    try:
                        shutil.rmtree(item)
                        logger.info(f"Removed directory: {item}")
                    except Exception as e:
                        logger.error(f"Failed to remove directory {item}: {e}")
        
        # Get the path to standard skills directory
        standard_skills_dir = Path(__file__).parent.parent.joinpath('standard_skills')
        
        if not standard_skills_dir.exists():
            logger.warning(f"Standard skills directory not found: {standard_skills_dir}")
            return
        
        # Log all files found in standard_skills directory before copying
        logger.info(f"Scanning standard skills directory: {standard_skills_dir}")
        all_standard_files = list(standard_skills_dir.rglob('*'))
        logger.info(f"Found {len(all_standard_files)} total items in standard_skills directory")
        
        # Log Python and markdown files that will be considered for copying
        skill_files_to_copy = []
        for item in all_standard_files:
            if item.is_file() and not item.name.startswith('__'):
                if item.suffix in ['.py', '.md']:
                    skill_files_to_copy.append(item)
                else:
                    logger.debug(f"Skipping non-skill file (wrong extension): {item.relative_to(standard_skills_dir)}")
            elif item.is_file() and item.name.startswith('__'):
                logger.debug(f"Skipping special file: {item.relative_to(standard_skills_dir)}")
        
        logger.info(f"Found {len(skill_files_to_copy)} skill files to copy from standard_skills")
        for skill_file in skill_files_to_copy:
            logger.info(f"  - {skill_file.relative_to(standard_skills_dir)}")
        
        copied_count = 0
        
        # If agent_id is specified, copy from agent-specific standard skills directory
        if self.agent_id:
            agent_standard_skills_dir = standard_skills_dir.joinpath(self.agent_id)
            if agent_standard_skills_dir.exists():
                # Copy all files (Python and markdown) from agent-specific standard_skills
                for skill_file in agent_standard_skills_dir.iterdir():
                    if skill_file.is_file() and not skill_file.name.startswith('__'):
                        try:
                            dest_file = self.skills_dir / skill_file.name
                            shutil.copy2(skill_file, dest_file)
                            logger.info(f"Copied agent-specific standard skill: {skill_file.name} to {dest_file}")
                            copied_count += 1
                        except Exception as e:
                            logger.error(f"Failed to copy agent skill {skill_file.name}: {e}")
        else:
            # Copy all files from standard_skills, preserving directory structure
            copied_count = self._copy_skills_preserving_structure(standard_skills_dir, self.skills_dir)
        
        if copied_count > 0:
            logger.info(f"Successfully copied {copied_count} standard skill(s) to {self.skills_dir}")
        else:
            logger.info("No standard skills found to copy")
    
    def _copy_skills_preserving_structure(self, source_dir: Path, dest_dir: Path) -> int:
        """
        Copy skills from source directory to destination directory, preserving structure.
        
        Args:
            source_dir: Source directory containing skills
            dest_dir: Destination directory to copy skills to
            
        Returns:
            Number of files copied
        """
        copied_count = 0
        skipped_count = 0
        
        # Walk through all files in source directory
        for item in source_dir.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(source_dir)
                
                # Check if file should be skipped
                if item.name.startswith('__'):
                    logger.info(f"Skipping special file: {rel_path}")
                    skipped_count += 1
                    continue
                
                # Skip non-Python and non-markdown files
                if item.suffix not in ['.py', '.md']:
                    logger.info(f"Skipping non-skill file (wrong extension {item.suffix}): {rel_path}")
                    skipped_count += 1
                    continue
                
                # Create destination path
                dest_file = dest_dir / rel_path
                
                # Create parent directories if they don't exist
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    shutil.copy2(item, dest_file)
                    logger.info(f"Copied skill: {rel_path} to {dest_file}")
                    copied_count += 1
                except Exception as e:
                    logger.error(f"Failed to copy skill {rel_path}: {e}")
        
        logger.info(f"Copy completed: {copied_count} files copied, {skipped_count} files skipped")
        return copied_count

    def scan_skills_directory(self) -> List[str]:
        """Scan the skills directory for Python files and return skill names."""
        skill_names = []
        
        if not self.skills_dir.exists():
            logger.info(f"Skills directory does not exist, creating: {self.skills_dir}")
            try:
                self.skills_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created skills directory: {self.skills_dir}")
            except Exception as e:
                logger.error(f"Failed to create skills directory {self.skills_dir}: {e}")
                return skill_names
            
        # Scan recursively for Python files
        for entry in self.skills_dir.rglob('*.py'):
            if entry.is_file() and not entry.name.startswith('__'):
                # Remove .py extension to get skill name
                skill_name = entry.stem
                skill_names.append(skill_name)
                
        return skill_names
    
    def scan_llm_skills(self) -> Dict[str, str]:
        """
        Scan for LLM/markdown skills (instruction files).
        
        Returns:
            Dictionary of skill_name -> skill_content
        """
        llm_skills = {}
        
        if not self.skills_dir.exists():
            return llm_skills
        
        # Scan recursively for .md files (LLM skills)
        for entry in self.skills_dir.rglob('*.md'):
            if entry.is_file() and not entry.name.startswith('__'):
                try:
                    skill_name = entry.stem
                    with open(entry, 'r', encoding='utf-8') as f:
                        content = f.read()
                    llm_skills[skill_name] = content
                    logger.info(f"Found LLM skill: {skill_name}")
                except Exception as e:
                    logger.error(f"Failed to read LLM skill {entry.name}: {e}")
        
        return llm_skills
    
    def should_scan(self) -> bool:
        """
        Check if it's time to scan skills directory.
        
        Returns:
            True if should scan, False otherwise
        """
        current_time = time.time()
        if current_time - self.last_scan_time >= self.scan_interval:
            return True
        return False
    
    def periodic_scan_and_reload(self) -> bool:
        """
        Periodically scan and reload skills if changes detected.
        
        Returns:
            True if skills were reloaded, False otherwise
        """
        if not self.should_scan():
            return False
        
        self.last_scan_time = time.time()
        
        # Get current skill files (recursively)
        current_skill_files = set()
        if self.skills_dir.exists():
            for entry in self.skills_dir.rglob('*'):
                if (entry.suffix in ['.py', '.md'] and 
                    entry.is_file() and 
                    not entry.name.startswith('__')):
                    # Use relative path to track files in subdirectories
                    rel_path = entry.relative_to(self.skills_dir)
                    current_skill_files.add(str(rel_path))
        
        # Check if skills have changed
        if current_skill_files != self.cached_skill_files:
            logger.info(f"Skills changed. Reloading... (Agent: {self.agent_id or 'shared'})")
            self.cached_skill_files = current_skill_files
            self.reload_skills()
            return True
        
        return False

    def load_register_skills_name(self) -> List[str]:
        """Get list of skill names from scanning the skills directory."""
        return self.scan_skills_directory()
    

    def load_skills(self) -> None:
        """Load all skills from the skills directory."""
        logger.info(f"Loading skills from directory: {self.skills_dir} (Agent: {self.agent_id or 'shared'})")
        
        # Load Python skills
        skill_names = self.scan_skills_directory()
        BaseLoading.object_type = BaseModel
        
        logger.info(f"Found {len(skill_names)} Python skill files to load")
        
        # Clear existing skills
        self.skill_object_list = []
        
        # Prepare kwargs to pass config to skills
        kwargs = {'config': self.config}
        
        # Determine extra_dir based on agent_id
        if self.agent_id:
            extra_dir = f'user_data/skills/{self.agent_id}'
        else:
            extra_dir = 'user_data/skills'
        
        for skill_name in skill_names:
            logger.debug(f"Loading skill: {skill_name}")
            
            # Find the actual file path for this skill
            skill_file_path = None
            for entry in self.skills_dir.rglob('*.py'):
                if entry.stem == skill_name and entry.is_file() and not entry.name.startswith('__'):
                    skill_file_path = entry
                    break
            
            if skill_file_path:
                # Calculate the directory containing the skill file
                skill_dir = skill_file_path.parent
                # Use the directory containing the skill file as extra_dir
                skill_extra_dir = str(skill_dir)
            else:
                # Fall back to default extra_dir
                skill_extra_dir = extra_dir
            
            try:
                # First try with the skill_name as-is (filename stem)
                skill = BaseLoading.load_object(
                    object_name=skill_name, 
                    config=self.config, 
                    kwargs=kwargs, 
                    extra_dir=skill_extra_dir
                )
                self.skill_object_list.append(skill)
                logger.info(f"✓ Successfully loaded skill: {skill_name}")
            except Exception as e:
                # If that fails, try converting snake_case to CamelCase
                # e.g., "task_management" -> "TaskManagement"
                try:
                    # Convert snake_case to CamelCase
                    camel_case_name = ''.join(word.capitalize() for word in skill_name.split('_'))
                    skill = BaseLoading.load_object(
                        object_name=camel_case_name, 
                        config=self.config, 
                        kwargs=kwargs, 
                        extra_dir=skill_extra_dir
                    )
                    self.skill_object_list.append(skill)
                    logger.info(f"✓ Successfully loaded skill: {skill_name} (as {camel_case_name})")
                except Exception as e2:
                    logger.error(f"✗ Failed to load skill {skill_name} (tried as {skill_name} and {camel_case_name}): {e2}", exc_info=True)
        
        logger.info(f"Loaded {len(self.skill_object_list)} Python skills successfully")
        
        # Load LLM/markdown skills
        self.llm_skills = self.scan_llm_skills()
        logger.info(f"Loaded {len(self.llm_skills)} LLM skills successfully")

    
    def reload_skills(self) -> None:
        """Reload all skills from the skills directory."""
        self.skill_object_list = []
        self.llm_skills = {}
        self.load_skills()


    def get_all_skills(self) -> List[BaseModel]:
        return self.skill_object_list
    
    def get_llm_skills(self) -> Dict[str, str]:
        """
        Get all LLM/markdown skills.
        
        Returns:
            Dictionary of skill_name -> skill_content
        """
        return self.llm_skills
    
    def search_skill_function_by_semantic_query(self, query: str, memory) -> List[BaseModel]:
        results = memory.search(
            collection_name=self.skills_area,
            query=query
        )
        return results
    
    def start_skill(self, memory: Any) -> None:
        # clear memory collection 
        if memory is not None:
            try:
                memory.delete_memory_collection(self.skills_area)
            except Exception as e:
                logger.info(f"Error deleting memory collection: {e}")

        self.load_skills()
        self.save_skills_function_to_memory(memory=memory)
    
    def remove_skill_by_name(self, skill_name: str, memory: Any) -> None:
        # clear memory collection 
        if memory is not None:
            try:
                memory.delete_memory_collection(self.skills_area)
            except Exception as e:
                logger.info(f"Error deleting memory collection: {e}")

        self.load_skills()
        self.skill_object_list = [skill for skill in self.skill_object_list if skill.__doc__ != skill_name]
        self.save_skills_function_to_memory(memory=memory)

    def save_skills_function_to_memory(self, memory: Any) -> None:
        if memory is None:
            logger.info("Memory is not available, skipping saving skills to memory.")
            return
            
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

