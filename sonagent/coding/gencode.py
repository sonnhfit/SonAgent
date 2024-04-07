import json
import logging
import os
from typing import Any, Dict, Union

import autogen
import yaml

from sonagent.coding.sonautogen import SonAutoGenAgent
from sonagent.llm.oai_llm import (auto_create_skill_docs,
                                  create_pull_request_info,
                                  rewrite_python_code_docs_string)
from sonagent.llm.prompt import DEFAULT_SYSTEM_MESSAGE_AUTO_GEN
from sonagent.persistence.models import SkillDocs

# llm_config = {
#     "config_list": [{"model": "gpt-4-0125-preview", "api_key": os.environ["OPENAI_API_KEY"]}],
# }

# config_list = [{"model": "gpt-4-0125-preview", "api_key": os.environ["OPENAI_API_KEY"]}]


class SonCodeAgent:
    def __init__(self, git_manager: Any = None, user_data_dir: str = '/user_data') -> None:
        self.user_data_dir = user_data_dir
        self.config_item = {"model": "gpt-4-0125-preview", "api_key": os.environ["OPENAI_API_KEY"]}
        self.llm_config = {
            "config_list": [
                self.config_item
            ],
        }
        self.config_list = [self.config_item]
        self.git_manager = git_manager
        

        # create an AssistantAgent named "assistant"
        self.assistant = autogen.AssistantAgent(
            name="assistant",
            system_message=DEFAULT_SYSTEM_MESSAGE_AUTO_GEN,
            llm_config={
                "cache_seed": 41,  # seed for caching and reproducibility
                "config_list": self.config_list,  # a list of OpenAI API configurations
                "temperature": 0,  # temperature for sampling
            },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API

        )

        self.user_proxy = SonAutoGenAgent(
            name="SonAgent",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={
                "work_dir": "coding",
                "use_docker": False,  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
            },
        )

        self.latest_code = None

    def add_skill_register_to_agent(self, skill_class: str, skill_file_path: str) -> None:

        with open(skill_file_path, 'r') as file:
            skills_register = yaml.safe_load(file)

        if skills_register['skills'] is None:
            skills_register['skills'] = []

        skills_register['skills'].append(skill_class)

        with open(skill_file_path, 'w') as file:
            yaml.dump(skills_register, file)

    def gen_code(self, message: str, is_create_pull_request: bool = False) -> Union[str, Dict[str, str]]:
        # generate code
        chat_res = self.user_proxy.initiate_chat(
            self.assistant,
            message=message,
            summary_method="reflection_with_llm",
        )

        self.latest_code = self.user_proxy.latest_code
        skill_name = ""

        if self.latest_code is None:
            logging.error("No code generated")
        else:
            self.latest_code = rewrite_python_code_docs_string(
                self.latest_code
            )
        
        metadata = {}
        pull_str = str(chat_res.summary) + "-- final code --" + str(self.latest_code)
        metadata_str = create_pull_request_info(pull_str)
        logging.info(f"metadata_str: {metadata_str}")
        
        # Removing the triple backticks and 'json' label
        json_str = metadata_str.replace("```json", "").replace("```", "")
        # Load the JSON data
        try:
            metadata = json.loads(json_str)
            print(metadata)
        except json.JSONDecodeError as e:
            print(f"____Error decoding JSON: {e}")

        skill_file_name = metadata.get("source_code_file_name", "default.py")

        if skill_file_name == "default.py":
            logging.error("No skill file name provided in metadata")


        if self.git_manager.name() == "github":
            # metadata = json.loads(metadata_str)
            code_branch = metadata.get("branch_name", "feature/sonagent-branch_name")
            
            if is_create_pull_request:
                # save code to current skill folder
                # {
                #     "branch_name": "feature/sonagent-google-search",
                #     "commit_message": "add new feature to perform Google search",
                #     "pull_request_title": "Add new skill to agent to perform Google search",
                #     "pull_request_body": "This pull request adds a new skill to the agent to perform a Google search using the googlesearch-python library.",
                #     "source_code_file_name": "skill_google_search.py",
                # }
                
                skill_file_path = f"{self.user_data_dir}/skills/{skill_file_name}"
                git_skill_file_path = f"user_data/skills/{skill_file_name}"

                # save to github skill folder
                # self.save_source_code(self.latest_code, code_path=skill_file_path)
                # user_data_dir = "user_data/skills"
                self.git_manager.create_branch(branch_name=code_branch)
                
                # write skill code
                self.git_manager.write_code(
                    code=self.latest_code, file_name=git_skill_file_path
                )

                # write skill register to skill file
                skill_class = metadata.get("class_name", None)
                if skill_class is not None and skill_class in str(chat_res.summary):
                    skill_file_path = f"{self.git_manager.local_repo_path}/user_data/skills/skills.yaml"
                    self.add_skill_register_to_agent(skill_class, skill_file_path)
                skill_name = skill_class
                commit_message = metadata.get("commit_message", "default commit message")
                self.git_manager.commit_and_push(code_branch, commit_message)
                pull_title = metadata.get("pull_request_title", "default pull request title")
                pull_body = metadata.get("pull_request_body", "default pull request body")

                pull_request_message = self.git_manager.create_pull_request(
                    code_branch, pull_title, pull_body, "main"
                )

                metadata['pull_request_message'] = pull_request_message

        elif self.git_manager.name() == "local":
            # save code to user_data folder clone from github
            git_skill_file_path = f"skills/{skill_file_name}"
            self.git_manager.write_code(
                code=self.latest_code, file_name=git_skill_file_path
            )

            # write skill register to skill file
            skill_class = metadata.get("class_name", None)
            if skill_class is not None and skill_class in str(pull_str):
                skill_file_path = f"{self.git_manager.local_repo_path}/skills/skills.yaml"
                self.add_skill_register_to_agent(skill_class, skill_file_path)
            skill_name = skill_class
        if self.latest_code is not None and skill_name != "":
            self.create_and_save_code_docs(skill_name, self.latest_code)

        return chat_res, metadata
    
    def save_source_code(self, code: str, code_path) -> None:
        # save code to user_data folder clone from github

        # save file to user data skill folder

        # open pull request to github
        pass
    
    def create_and_save_code_docs(self, skill_name: str, code: str) -> None:
        try:
            docs = auto_create_skill_docs(code)
            logging.info(f"Docs: {docs}")
            # save docs to models
            plan = SkillDocs(skill_name=skill_name, docs=docs)
            SkillDocs.session.add(plan)
            SkillDocs.session.commit()


        except Exception as e:
            logging.error(f"Error creating code docs: {e}")
            return None


