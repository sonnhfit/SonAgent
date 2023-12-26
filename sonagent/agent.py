from sonagent.persistence.models import init_db
from sonagent.persistence.belief_models import Belief
from sonagent.memory.memory import SonMemory


class Agent:
    def __init__(self, memory_path) -> None:
        # persistence
        init_db("sqlite:///user_data/agentdb.sqlite")

        # memory
        self.memory = SonMemory(default_memory_path=memory_path)

        # planner

    
    def run(self, input) -> None:
        print("Hello, world!")
        # self._create_belief("my name is Son", "this is my name")
        self.sync_beliefs()

    def sync_beliefs(self) -> None:
        list_belief = Belief.get_all_belief()
        for belief in list_belief:
            self.memory.add(belief.text, {"description": belief.description}, str(belief.id))


    def _create_belief(self, text: str, description: str) -> None:
        belief = Belief(text=text, description=description)
        Belief.session.add(belief)
        Belief.session.commit()
        # Belief.commit()
        

    def get_tools(self) -> list:
        
        return []
