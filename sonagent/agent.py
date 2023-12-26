import logging

from sonagent.persistence.models import init_db
from sonagent.persistence.belief_models import Belief
from sonagent.memory.memory import SonMemory


logger = logging.getLogger(__name__)

class Agent:
    def __init__(self, memory_path) -> None:
        # persistence
        init_db("sqlite:///user_data/agentdb.sqlite")

        

        # memory
        self.memory = SonMemory(default_memory_path=memory_path)

        # planner


        # self.sync_beliefs()

    def run(self, input) -> None:
        # get belief -> thinking, planning -> acting

        belief = self.memory.brain_area_search(area_collection_name="belief_base", query=input)
        print(belief)

        # self._create_belief("my name is Son", "this is my name")
        

    def sync_beliefs(self) -> None:
        logger.debug("Start syncing beliefs to memory.")
        list_belief = Belief.get_all_belief()
        print(list_belief)
        for belief in list_belief:
            self.memory.add(belief.text, {"description": belief.description}, str(belief.id), area_collection_name="belief_base")
        logger.debug("Finish syncing beliefs to memory.")

    def create_belief(self, text: str, description: str) -> None:
        belief = Belief(text=text, description=description)
        Belief.session.add(belief)
        Belief.session.commit()
        logger.debug("Finish Create new belief.")
        # Belief.commit()

    def clear_all_beliefs(self) -> None:
        Belief.session.query(Belief).delete()
        Belief.session.commit()

        logger.debug("Finish delete all belief.")

    def delete_everything(self) -> None:
        self.clear_all_beliefs()
        self.memory.clear_all()
        logger.debug("Finish delete everything.")

    def get_tools(self) -> list:
        return []
    
