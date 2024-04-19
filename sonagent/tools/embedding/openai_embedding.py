from sonagent.tools.embedding.embedding import Embedding
from openai import OpenAI
import os


class OAIEmbedding(Embedding):
    def __init__(self):
        super().__init__('openai')
        api_key = os.environ.get('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key)

    def embed(self, text: str):
        response = self.client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return {"text": response.data[0].embedding}

    def embed_batch(self, texts):
        result = {}
        response = self.client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        for i, text in enumerate(texts):
            result[text] = response.data[i].embedding
        return result
