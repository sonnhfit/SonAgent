import os
import chromadb


class SonMemory:

    def __init__(self, collection_name="son_memory", memory_init_mode="file", default_memory_path=None):
        self.memory_type = None
        self.chroma_client = None
        self.memory_collection = None

        if memory_init_mode == "file":
            self.chroma_client = chromadb.PersistentClient(
                path=default_memory_path
            )
        elif memory_init_mode == "server":
            self.chroma_client = chromadb.HttpClient(
                host='localhost',
                port=8000
            )
        else:
            self.chroma_client = chromadb.Client()

        
        if self.chroma_client != None:
            self.memory_collection = self.chroma_client.get_or_create_collection(name=collection_name)
        else:
            self.memory_collection = None


    def set_memory_collection(self, collection_name=None):
        if self.chroma_client != None:
            self.memory_collection = self.chroma_client.get_collection(name=collection_name)
        else:
            self.memory_collection = None


    def search(self, query, n_results=10):
        results = self.memory_collection.query(
            query_texts=[query],
            n_results=n_results
        )

        return results
    

    def add(self, document: str="", metadata: dict={}, id: str=""):
        self.memory_collection.add(
            documents=[document],
            metadatas=[metadata],
            ids=[id]
        )

        
    def search_with_embedding(self, embedding):
        pass

    def save(self):
        pass
    
    def delete(self):
        pass

    def load(self):
        pass

    def reset_memory(self):
        self.chroma_client.reset()

