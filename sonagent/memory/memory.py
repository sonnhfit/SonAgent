import logging

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)
class SonMemory:

    def __init__(self, collection_name="son_memory", memory_init_mode="file", default_memory_path=None):
        self.memory_type = None
        self.chroma_client = None
        self.memory_collection = None

        if memory_init_mode == "file":
            self.chroma_client = chromadb.PersistentClient(
                path=default_memory_path,
                settings=Settings(allow_reset=True)
            )
        elif memory_init_mode == "server":
            self.chroma_client = chromadb.HttpClient(
                host='localhost',
                port=8000
            )
        else:
            self.chroma_client = chromadb.Client()

        
        if self.chroma_client is not None:
            self.memory_collection = self.chroma_client.get_or_create_collection(name=collection_name)
        else:
            self.memory_collection = None


    def set_memory_collection(self, collection_name=None):
        if self.chroma_client is not None:
            self.memory_collection = self.chroma_client.get_collection(name=collection_name)
        else:
            self.memory_collection = None

    def delete_memory_collection(self, collection_name=None):
        if self.chroma_client is not None:
            self.chroma_client.delete_collection(name=collection_name)
            return True
        return False

    def search(self, query, n_results=10):
        results = self.memory_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
    
    def brain_area_search(self, query, area_collection_name, n_results=10):
        area_collection = self.chroma_client.get_or_create_collection(
            name=area_collection_name
        )

        logger.debug(f"Searching in brain area {area_collection_name} with query {query}")
        
        results = area_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        logger.debug(f"results {results}")

        return results
    

    def add(self, document: str="", metadata: dict={}, id: str="", area_collection_name=None):
        try:
            if area_collection_name is not None:
                area_collection = self.chroma_client.get_or_create_collection(
                    name=area_collection_name
                )
                area_collection.add(
                    documents=[document],
                    metadatas=[metadata],
                    ids=[id]
                )
                return True
            else:
                self.memory_collection.add(
                    documents=[document],
                    metadatas=[metadata],
                    ids=[id]
                )
                return True
        except Exception as e:
            print(e)
            return False

        
    def search_with_embedding(self, embedding):
        pass

    def save(self):
        pass
    
    def clear_all(self):
        self.chroma_client.reset()

    def load(self):
        pass

    def reset_memory(self):
        self.chroma_client.reset()

