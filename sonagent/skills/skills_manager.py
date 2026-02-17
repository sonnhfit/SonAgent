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
        
        # Get the path to standard skills directory
        standard_skills_dir = Path(__file__).parent.parent.joinpath('standard_skills')
        
        if not standard_skills_dir.exists():
            logger.warning(f"Standard skills directory not found: {standard_skills_dir}")
            return
        
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
            # Copy all Python files from standard_skills root to user_data/skills (shared skills)
            for skill_file in standard_skills_dir.iterdir():
                if skill_file.suffix == '.py' and skill_file.is_file() and not skill_file.name.startswith('__'):
                    try:
                        dest_file = self.skills_dir / skill_file.name
                        shutil.copy2(skill_file, dest_file)
                        logger.info(f"Copied standard skill: {skill_file.name} to {dest_file}")
                        copied_count += 1
                    except Exception as e:
                        logger.error(f"Failed to copy skill {skill_file.name}: {e}")
        
        if copied_count > 0:
            logger.info(f"Successfully copied {copied_count} standard skill(s) to {self.skills_dir}")
        else:
            logger.info("No standard skills found to copy")

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
            
        for entry in self.skills_dir.iterdir():
            if entry.suffix == '.py' and entry.is_file() and not entry.name.startswith('__'):
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
        
        # Scan for .md files (LLM skills)
        for entry in self.skills_dir.iterdir():
            if entry.suffix == '.md' and entry.is_file() and not entry.name.startswith('__'):
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
        
        # Get current skill files
        current_skill_files = set()
        if self.skills_dir.exists():
            for entry in self.skills_dir.iterdir():
                if (entry.suffix in ['.py', '.md'] and 
                    entry.is_file() and 
                    not entry.name.startswith('__')):
                    current_skill_files.add(entry.name)
        
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
            try:
                skill = BaseLoading.load_object(
                    object_name=skill_name, 
                    config=self.config, 
                    kwargs=kwargs, 
                    extra_dir=extra_dir
                )
                self.skill_object_list.append(skill)
                logger.info(f"✓ Successfully loaded skill: {skill_name}")
            except Exception as e:
                logger.error(f"✗ Failed to load skill {skill_name}: {e}", exc_info=True)
        
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

