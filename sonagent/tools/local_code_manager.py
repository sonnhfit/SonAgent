
import logging
import os
import shutil
from pathlib import Path

import requests

from sonagent.tools.code_manager import CodeManager

logger = logging.getLogger(__name__)


class LocalCodeManager(CodeManager):
    def __init__(
        self, local_repo_path: str
    ) -> None:
        self.local_repo_path = local_repo_path

    def name(self) -> str:
        return "local"
    
    def write_code(self, file_name: str, code: str) -> str:
        file_path = f"{self.local_repo_path}/{file_name}"
        path_ = Path(file_path)
        dir_path = str(path_.parent.absolute())
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with open(file_path, "w") as file:
            file.write(code)
        return file_path
    
    def read_code(self, file_name: str) -> str:
        file_path = f"{self.local_repo_path}/{file_name}"
        with open(file_path, "r") as file:
            return file.read()
        
    def summary_code(self, file_name: str) -> str:
        pass

    def create_readme_tree(self, content: str) -> str:
        file_path = f"{self.local_repo_path}/README.md"
        with open(file_path, "w") as file:
            file.write(content)
        return file_path
