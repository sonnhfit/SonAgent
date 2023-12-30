import logging

from sonagent.persistence.models import init_db
from sonagent.persistence.belief_models import Belief
from sonagent.memory.memory import SonMemory
from sonagent.planning.planner import SonAgentPlanner
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from sonagent.planning.prompt import PROMPT_PLAN



logger = logging.getLogger(__name__)

class Agent:
    def __init__(self, memory_path) -> None:
        # persistence
        init_db("sqlite:///user_data/agentdb.sqlite")

        

        # memory
        self.memory = SonMemory(default_memory_path=memory_path)
        

        # planner

        self.planner = SonAgentPlanner()


        # self.sync_beliefs()
    
    def get_beliefs_for_planner(self, ids: list) -> list:
        list_belief = Belief.get_belief_by_ids(ids=ids)
        return list_belief


    async def run(self, input) -> None:
        # get belief -> thinking, planning -> acting

        belief = self.memory.brain_area_search(area_collection_name="belief_base", query=input)
        belief_ids = belief['ids'][0]
        result_list = self.get_beliefs_for_planner(belief_ids)
        belief_text = ""
        for item in result_list:
            belief_text += item.text

        deployment, api_key, endpoint = sk.azure_openai_settings_from_dot_env()
        # print(deployment, api_key, endpoint)
        kernel = sk.Kernel()
        kernel.add_chat_service("chat_completion", AzureChatCompletion(deployment, endpoint, api_key))

        # planner = SonAgentPlanner()
        ask = "train a neural network for classify 0 -> 9?"
        # plan = await planner.create_plan_async(ask, kernel)
        # print(plan.generated_plan)

        variables = sk.ContextVariables()

        variables['believe'] = belief_text
        variables['goal'] = ask

        semantic_function = kernel.create_semantic_function(
            PROMPT_PLAN
        )
        result = await kernel.run_async(
            semantic_function,
            input_vars=variables,
        )
        print(result)
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
    
