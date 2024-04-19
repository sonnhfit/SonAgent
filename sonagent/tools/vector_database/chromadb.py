import chromadb
from sonagent.tools.vector_database.vectordb import VectorDB


class ChromaDB(VectorDB):
    def __init__(self, host: str = "localhost", port: int = 8000):
        super().__init__(db_path='')
        self.client = chromadb.HttpClient(host=host, port=port)

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
