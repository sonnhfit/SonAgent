from abc import ABC

import chromadb
from chromadb.config import Settings


class VectorDB(ABC):
    def __init__(self, db_path):
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(allow_reset=True)
        )

    def add(
        self,
        embeddings: list,
        metadatas: list,
        docs: list,
        ids: list,
        collection: str = "",
    ):
        collection = self.client.get_or_create_collection(name=collection)
        collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            documents=docs,
            ids=ids,
        )

    def query(self, embedding: list, k: int, collection: str = ""):
        collection = self.client.get_or_create_collection(name=collection)
        result = collection.query(
            query_embeddings=[embedding],
            n_results=k
        )
        return result
    
    def get_collection(self, collection_name):
        return self.client.get_collection(collection_name)
    
    def delete_collection(self, collection_name):
        return self.client.delete_collection(collection_name)
    
    def reset(self):
        return self.client.reset()
