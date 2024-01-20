
from sonagent.memory.memory import SonMemory

class ShortTermMemory(SonMemory):

    def __init__(self, collection_name="short_term_memory", memory_init_mode="file", default_memory_path=None):
        super().__init__(collection_name=collection_name, memory_init_mode=memory_init_mode, default_memory_path=default_memory_path)

        self.chat_dialog = []

    def add_chat_item(self, item: dict={}):
        self.chat_dialog.append(item)

    def get_chat_dialog(self) -> list:
        return self.chat_dialog
    
    def get_chat_dialog_as_string(self):
        return " ".join(self.chat_dialog)
    
    def clear_chat_dialog(self):
        self.chat_dialog = []

    def extract_belief_from_chat_dialog(self):
        belief = " ".join(self.chat_dialog)
        return belief

