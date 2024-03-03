import autogen
from typing import Callable, Dict, List, Literal, Optional, Union
from autogen import ConversableAgent

from autogen.runtime_logging import logging_enabled, log_new_agent
from autogen.code_utils import (
    UNKNOWN,
    content_str,
    check_can_use_docker_or_throw,
    decide_use_docker,
    execute_code,
    extract_code,
    infer_lang,
)

class SonAutoGenAgent(autogen.ConversableAgent):
    DEFAULT_USER_PROXY_AGENT_DESCRIPTIONS = {
        "ALWAYS": "An attentive HUMAN user who can answer questions about the task, and can perform tasks such as running Python code or inputting command line commands at a Linux terminal and reporting back the execution results.",
        "TERMINATE": "A user that can run Python code or input command line commands at a Linux terminal and report back the execution results.",
        "NEVER": "A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks).",
    }

    def __init__(
        self,
        name: str,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "ALWAYS",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        llm_config: Optional[Union[Dict, Literal[False]]] = False,
        system_message: Optional[Union[str, List]] = "",
        description: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
            description=description
            if description is not None
            else self.DEFAULT_USER_PROXY_AGENT_DESCRIPTIONS[human_input_mode],
        )
        self.latest_code = None

        if logging_enabled():
            log_new_agent(self, locals())

        
    def save_source_code(self, code):
        # f = open(f"{localRepopath}/demofile.py", "w")
        # f.write(code)
        # f.close()
        self.latest_code = code
        
    def run_code(self, code, **kwargs):
        """Run the code and return the result.
    
        Override this function to modify the way to run the code.
        Args:
            code (str): the code to be executed.
            **kwargs: other keyword arguments.
    
        Returns:
            A tuple of (exitcode, logs, image).
            exitcode (int): the exit code of the code execution.
            logs (str): the logs of the code execution.
            image (str or None): the docker image used for the code execution.
        """
        self.save_source_code(code)
        return execute_code(code, **kwargs)
