import os
import autogen
from typing import Dict, Union
from sonagent.coding.sonautogen import SonAutoGenAgent


# llm_config = {
#     "config_list": [{"model": "gpt-4-0125-preview", "api_key": os.environ["OPENAI_API_KEY"]}],
# }

# config_list = [{"model": "gpt-4-0125-preview", "api_key": os.environ["OPENAI_API_KEY"]}]


class SonCodeAgent:
    def __init__(self) -> None:
        self.config_item = {"model": "gpt-4-0125-preview", "api_key": os.environ["OPENAI_API_KEY"]}
        self.llm_config = {
            "config_list": [
                self.config_item
            ],
        }
        self.config_list = [self.config_item]

        # create an AssistantAgent named "assistant"
        self.assistant = autogen.AssistantAgent(
            name="assistant",
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

    def gen_code(self, message: str) -> Union[str, Dict[str, str]]:
        # generate code
        chat_res = self.user_proxy.initiate_chat(
            self.assistant,
            message=message,
            summary_method="reflection_with_llm",
        )
        
        return chat_res





