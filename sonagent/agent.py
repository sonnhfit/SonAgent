from sonagent.persistence.models import init_db


class Agent:
    def __init__(self) -> None:
        init_db("sqlite:///user_data/agentdb.sqlite")
    
    def run(self) -> None:
        print("Hello, world!")
