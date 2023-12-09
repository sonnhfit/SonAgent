class Chat:
    def __init__(self, chat_id, chat_type, chat_name):
        self.chat_id = chat_id
        self.chat_type = chat_type
        self.chat_name = chat_name
        self.chat_dialog = []

    def start(self):
        print("Hello, world!")

    def run(self, input):
        print("Hello, world!")
    
    def stop(self, input):
        print("Goodbye, world!")

    def __str__(self):
        return f"Chat(chat_id={self.chat_id}, chat_type={self.chat_type}, chat_name={self.chat_name})"

    def __repr__(self):
        return self.__str__()
