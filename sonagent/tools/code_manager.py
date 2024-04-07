import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CodeManager(ABC):
    @abstractmethod
    def write_code(self, file_name: str, code: str) -> str:
        pass

    @abstractmethod
    def read_code(self, file_name: str) -> str:
        pass

    @abstractmethod
    def summary_code(self, file_name: str) -> str:
        pass

    @abstractmethod
    def create_readme_tree(self, content: str) -> str:
        pass

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()
