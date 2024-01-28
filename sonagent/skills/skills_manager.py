import logging
from collections import deque
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, Union

from semantic_kernel.sk_pydantic import SKBaseModel
import yaml
from sonagent.skills.loading import BaseLoading

logger = logging.getLogger(__name__)


class SkillsManager:

    # load, and get skills from config

    def __init__(self, sonagent) -> None:
        self.skill_object_list: List[SKBaseModel] = []
        self.config = sonagent.config

    def load_register_skills_name(self) -> List[str]:
        skill_file_name = self.config.get('skills_file_path', 'skill.yaml')
        skill_file_path = Path(self.config['user_data_dir']).joinpath(skill_file_name)
        with open(skill_file_path, 'r') as file:
            skills_register = yaml.safe_load(file)

        return skills_register['skills']
    

    def load_skills(self) -> None:
        skills_register = self.load_register_skills_name()
        BaseLoading.object_type = SKBaseModel
        for skill_name in skills_register:
            skill = BaseLoading.load_object(object_name=skill_name, config=self.config, kwargs={}, extra_dir='user_data_example/skills')
            self.skill_object_list.append(skill)

    
    def get_all_skills(self) -> List[SKBaseModel]:
        return self.skill_object_list
