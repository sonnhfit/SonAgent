
import logging
from abc import ABC, abstractmethod

from semantic_kernel.sk_pydantic import SKBaseModel


class SonSkill(ABC, SKBaseModel):

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()
    
    # @staticmethod
    

