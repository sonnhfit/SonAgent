import os
from typing import List

from openai import OpenAI

from sonagent.tools.embedding.embedding import Embedding


class OAIEmbedding(Embedding):
    def __init__(self):
        super().__init__('openai')
        api_key = os.environ.get('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key)

    def embed(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [item.embedding for item in response.data]
