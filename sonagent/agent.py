from sonagent.persistence.models import init_db


class Agent:
    def __init__(self) -> None:
        init_db("sqlite:///user_data/agentdb.sqlite")
    
    def run(self, input) -> None:
        print("Hello, world!")


    def get_tools(self) -> list:
        
        return []
