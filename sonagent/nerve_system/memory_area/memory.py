import logging
from sonagent.nerve_system.brain_lobe import BrainLobe

from sonagent.tools import ChromaDB, Embedding, OAIEmbedding, VectorDB

logger = logging.getLogger(__name__)


class SonMemory(BrainLobe):

    def __init__(
        self,
        collection_name="son_memory",
        memory_type="file",
        embedding_type="openai",
        default_memory_path=None,
        **kwargs
    ):
        self.memory_type = None
        self.vtdb: VectorDB = None
        self.embed: Embedding = None

        self.chroma_client = None
        self.memory_collection = collection_name

        # setup vector database
        if memory_type == "file":
            self.vtdb = VectorDB(db_path=default_memory_path)
        
        elif memory_type == "chromadb":
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 8000)
            self.vtdb = ChromaDB(host=host, port=port)
            
        elif memory_type == "qdrand":
            # TODO: Implement QDRand memory
            pass

        # setup embedding
        if embedding_type == "openai":
            self.embed = OAIEmbedding()

    def delete_memory_collection(self, collection_name=None):
        if self.vtdb is not None:
            self.vtdb.delete_collection(collection_name)
            return True
        return False

    def search(self, query, n_results=10, collection_name=None):
        if collection_name is None:
            collection_name = self.memory_collection
        
        logger.debug(
            f"Searching in brain area {collection_name} with query {query}"
        )

        embedding = self.embed.embed(query)
        results = self.vtdb.query(
            embedding=embedding, k=n_results, collection=collection_name
        )
        return results

    def add(
        self,
        document: str = "",
        metadata: dict = {},
        id: str = "",
        collection_name=None,
    ):
        if collection_name is None:
            collection_name = self.memory_collection

        try:
            self.vtdb.add(
                embeddings=[self.embed.embed(document)],
                docs=[document], metadatas=[metadata], ids=[id],
                collection=collection_name
            )
            return True
        except Exception as e:
            print(e)
            return False

    def clear_all(self):
        self.vtdb.reset()

    def reset_memory(self):
        self.vtdb.reset()
