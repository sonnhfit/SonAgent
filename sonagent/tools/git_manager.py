import logging
import requests
import git
import shutil
import os
from pathlib import Path
from sonagent.tools.code_manager import CodeManager

logger = logging.getLogger(__name__)


class GitManager(CodeManager):

    def __init__(
        self, username: str, repo_name: str,
        token: str, local_repo_path: str
    ) -> None:
        self.username = username
        self.repo_name = repo_name
        self.token = token
        self.local_repo_path = local_repo_path
        self.remote_repo_path = (
            f"https://{self.username}:{self.token}"
            f"@github.com/{self.username}/{self.repo_name}.git"
        )

        # clone source code when init
        try:
            self.repo = git.Repo.clone_from(
                self.remote_repo_path,
                self.local_repo_path
            )
        except Exception as e:
            logger.info(
                f"Local repo already exists, removing and cloning again. {e}"
            )
            shutil.rmtree(self.local_repo_path)
            self.repo = git.Repo.clone_from(
                self.remote_repo_path,
                self.local_repo_path
            )

    def name(self) -> str:
        return "github"

    def create_branch(self, branch_name: str) -> None:
        origin = self.repo.remote(name="origin")
        new_branch = self.repo.create_head(
            branch_name, origin.refs.main
        )
        new_branch.checkout()
        return branch_name
    
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

    def commit_and_push(self, branch_name: str, commit_message: str) -> None:
        self.repo.git.add(A=True)
        self.repo.index.commit(commit_message)
        origin = self.repo.remote(name="origin")
        # origin.push(refspec=f"{branch_name}:{branch_name}")
        self.repo.git.push("--set-upstream", origin, branch_name)

    def create_pull_request(
        self, branch_name: str, title: str, body: str, base_branch: str
    ) -> None:
        url = f"https://api.github.com/repos/{self.username}/{self.repo}/pulls"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        data = {
            "title": title,
            "body": body,
            "head": branch_name,
            "base": base_branch
        }
        response = requests.post(url, headers=headers, json=data)
        return response.json()
