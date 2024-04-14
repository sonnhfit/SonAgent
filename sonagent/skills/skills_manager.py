import logging
from pathlib import Path
from typing import Any, List

import yaml
from pydantic import BaseModel

from sonagent.skills.loading import BaseLoading
from sonagent.utils.utils import hash_md5_str

logger = logging.getLogger(__name__)


class SkillsManager:

    # load, and get skills from config

    def __init__(self, sonagent) -> None:
        self.skill_object_list: List[BaseModel] = []
        self.config = sonagent.config
        self.skills_area = "son_skills"

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
        results = memory.brain_area_search(
            area_collection_name=self.skills_area,
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
            # skill_hash_str(skill.name())
            is_added = memory.add(
                document=skill.__doc__,
                metadata={'skill_description': skill.__doc__},
                id=hash_md5_str(skill.__doc__),
                area_collection_name=self.skills_area
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

