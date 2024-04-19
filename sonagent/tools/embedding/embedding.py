from abc import ABC, abstractmethod


class Embedding(ABC):
    def __init__(self, embedding_type):
        self.embedding_type = embedding_type

    @abstractmethod
    def embed(self, text: str):
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]):
        pass
