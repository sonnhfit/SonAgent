
import logging
from semantic_kernel.sk_pydantic import SKBaseModel
from abc import ABC, abstractmethod 


class SonSkill(ABC, SKBaseModel):

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()
    
    # @staticmethod
    

