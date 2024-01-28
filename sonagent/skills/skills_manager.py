import logging
from collections import deque
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, Union

from semantic_kernel.sk_pydantic import SKBaseModel
import yaml
from sonagent.skills.loading import BaseLoading
from sonagent.skills.skills import SonSkill
from sonagent.utils.utils import hash_str

logger = logging.getLogger(__name__)


class SkillsManager:

    # load, and get skills from config

    def __init__(self, sonagent) -> None:
        self.skill_object_list: List[SonSkill] = []
        self.config = sonagent.config
        self.skills_area = "son_skills"

    def load_register_skills_name(self) -> List[str]:
        skill_file_name = self.config.get('skills_file_path', 'skill.yaml')
        skill_file_path = Path(self.config['user_data_dir']).joinpath(skill_file_name)
        with open(skill_file_path, 'r') as file:
            skills_register = yaml.safe_load(file)

        return skills_register['skills']
    

    def load_skills(self) -> None:
        skills_register = self.load_register_skills_name()
        BaseLoading.object_type = SonSkill
        for skill_name in skills_register:
            skill = BaseLoading.load_object(object_name=skill_name, config=self.config, kwargs={}, extra_dir='user_data_example/skills')
            self.skill_object_list.append(skill)

    
    def get_all_skills(self) -> List[SonSkill]:
        return self.skill_object_list
    
    def search_skill_function_by_semantic_query(self, query: str, memory) -> List[SonSkill]:
        results = memory.brain_area_search(
            area_collection_name=self.skills_area,
            query=query
        )
        return results

    def save_skills_function_to_memory(self, memory: Any) -> None:
        for skill in self.skill_object_list:
            # skill_hash_str(skill.name())
            is_added = memory.add(
                document="",
                metadata={},
                id=skill.name(),
                area_collection_name=self.skills_area
            )
            if is_added:
                logger.info(f"Skill {skill.name()} added to memory.")
    
    def get_available_function_skills(self) -> List[SonSkill]:
        # Search for functions that match the semantic query.

        # Add functions that were found in the search results.

        # Add any missing functions that were included but not found in the search results.

        return ""

