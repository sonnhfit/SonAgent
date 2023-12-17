import chromadb


class BaseMemory:

    def __init__(self):
        self.memory_type = None
        self.chroma_client = chromadb.Client()

    def search(self, query):
        pass

    def save(self):
        pass
    
    def delete(self):
        pass

    def load(self):
        pass
