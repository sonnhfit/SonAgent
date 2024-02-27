import os
import logging

from sonagent.persistence import Belief, Plan

from sonagent.memory.memory import SonMemory
from sonagent.memory.short_memory import ShortTermMemory
from sonagent.planning.planner import SonAgentPlanner, SonAgentSequentialPlanner
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatCompletion
import semantic_kernel.connectors.ai.open_ai as sk_oai
from semantic_kernel.planning.sequential_planner.sequential_planner_parser import (
    SequentialPlanParser,
)

from sonagent.planning.prompt import PROMPT_PLAN, SEQUENCE_PLAN, CLEAN_BELIEF_PROMPT
from sonagent.core_prompt.me import ASK_ABOUT_ME_PROMP
from sonagent.coding.gencode import SonCodeAgent

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, memory_path, skills, config: dict) -> None:
        # memory
        logger.debug(f"init memory with path {memory_path}.")
        self.memory = SonMemory(default_memory_path=memory_path)
        self.short_term_memory = ShortTermMemory(
            collection_name="short_term_memory", default_memory_path=memory_path
        )
        self.config = config

        # planner
        self.planner = SonAgentPlanner()
        # self.sync_beliefs()

        self.skills = skills
        self.skills.start_skill(memory=self.memory)
        openai = self.config.get('openai')
        if openai.get('api_type', None) == 'openai':
            self.chat_service = OpenAIChatCompletion(
                ai_model_id="gpt-4-0125-preview", api_key=os.environ["OPENAI_API_KEY"]
            )
        elif openai.get('api_type', None) == 'azure':
            deployment, api_key, endpoint = sk.azure_openai_settings_from_dot_env()
            self.chat_service = AzureChatCompletion(
                deployment_name=deployment, endpoint=endpoint, api_key=api_key
            )

        # print(deployment, api_key, endpoint)
        self.kernel = sk.Kernel()
        
        self.kernel.add_chat_service(
            "chat_completion",
            self.chat_service
        )

        self.codeagent = SonCodeAgent()

    def save_function_to_memory(self, function_name: str) -> None:
        pass

    def get_beliefs_for_planner(self, ids: list) -> list:
        list_belief = Belief.get_belief_by_ids(ids=ids)
        return list_belief

    async def run(self, input) -> None:
        # get belief -> thinking, planning -> acting

        belief = self.memory.brain_area_search(
            area_collection_name="belief_base", query=input
        )
        belief_ids = belief["ids"][0]
        result_list = self.get_beliefs_for_planner(belief_ids)
        belief_text = ""
        for item in result_list:
            belief_text += item.text

        deployment, api_key, endpoint = sk.azure_openai_settings_from_dot_env()
        # print(deployment, api_key, endpoint)
        kernel = sk.Kernel()
        kernel.add_chat_service(
            "chat_completion",
            AzureChatCompletion(
                deployment_name=deployment, endpoint=endpoint, api_key=api_key
            ),
        )

        # planner = SonAgentPlanner()
        ask = "train a neural network for classify 0 -> 9?"
        # plan = await planner.create_plan_async(ask, kernel)
        # print(plan.generated_plan)

        variables = sk.ContextVariables()

        variables["believe"] = belief_text
        variables["goal"] = ask

        semantic_function = kernel.create_semantic_function(PROMPT_PLAN)
        result = await kernel.run_async(
            semantic_function,
            input_vars=variables,
        )
        print(result)
        print(type(result))
        print("plan: ", result.json())

        print("skill: ", result.skills)

        # self._create_belief("my name is Son", "this is my name")

    def sync_beliefs(self) -> None:
        logger.debug("Start syncing beliefs to memory.")
        list_belief = Belief.get_all_belief()

        for belief in list_belief:
            self.memory.add(
                belief.text,
                {"description": belief.description},
                str(belief.id),
                area_collection_name="belief_base",
            )
        logger.info("Finish syncing beliefs to memory.")

    def create_beslief(self, text: str, description: str) -> None:
        try:
            belief = Belief(text=text, description=description)
            Belief.session.add(belief)
            Belief.session.commit()
            logger.debug("Finish Create new belief.")
            # Belief.commit()
        except Exception as e:
            logger.error(f"Error create belief: {e}")

    def clear_all_beliefs(self) -> None:
        Belief.session.query(Belief).delete()
        Belief.session.commit()

        logger.debug("Finish delete all belief.")

    def delete_everything(self) -> bool:
        try:
            self.clear_all_beliefs()
            self.memory.clear_all()
            logger.debug("Finish delete everything.")
        except Exception as e:
            logger.error(f"Error delete everything: {e}")
            return False
        return True

    def get_tools(self) -> list:
        return []

    async def chat(self, input: str) -> str:
        self.short_term_memory.add_chat_item({"role": "user", "content": input})
        message_text = self.short_term_memory.get_chat_dialog()

        logger.info(f"Start chat: {message_text}")
        res = await self.chat_service.complete_chat_async(
            messages=message_text,
            settings=sk_oai.AzureChatRequestSettings(
                temperature=0.7,
                max_tokens=2500,
                top_p=0.8,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop=[],
            ),
        )
        response = str(res[0])
        
        self.short_term_memory.add_chat_item({"role":"assistant","content":str(response)})
        logger.info(f"Finish chat: {str(response)}")

        return str(response)

    async def clear_short_term_memory(self) -> str:
        self.short_term_memory.clear_chat_dialog()
        return "Clear short term memory successfully."
    
    async def ibelieve(self, input: str) -> bool:
        # maybe that gen by LLM + your input
        try:
            self.create_beslief(input, input)
            self.sync_beliefs()
        except Exception as e:
            logger.error(f"Error gen belief: {e}")
            return False
        return True

    async def askme(self, question: str) -> str:
        # get belief
        logger.debug(f"Start asking: Q: {question}")

        belief = self.memory.brain_area_search(
            area_collection_name="belief_base", query=question
        )

        belief_ids = belief["ids"][0]

        logger.debug(f"belief_ids: {belief_ids}")

        result_list = self.get_beliefs_for_planner(belief_ids)

        logger.debug(f"result_list: {result_list}")

        belief_text = ""
        for item in result_list:
            belief_text += str("-" + item.text + "\n")

        logger.info(f"Belief_text: \n{belief_text}")

        # answer by belief
        semantic_function = self.kernel.create_semantic_function(
            ASK_ABOUT_ME_PROMP, max_tokens=2500, temperature=0.7, top_p=0.8
        )

        variables = sk.ContextVariables()

        variables["believe"] = belief_text
        variables["question"] = question

        result = await self.kernel.run_async(
            semantic_function,
            input_vars=variables,
        )
        logger.debug("Finish asking.")
        return str(result)

    async def reincarnate(self) -> str:
        if self.delete_everything():
            return "Reincarnate successfully."
        else:
            return "Reincarnate failed."

    async def planning(self, goal: str) -> str:

        belief = self.memory.brain_area_search(
            area_collection_name="belief_base", query=goal
        )
        belief_ids = belief["ids"][0]
        result_list = self.get_beliefs_for_planner(belief_ids)

        belief_text = ""
        for item in result_list:
            belief_text += str("-" + item.text + "\n")

        # clean belief
        
        clean_belief_semantic_function = self.kernel.create_semantic_function(CLEAN_BELIEF_PROMPT)
        clean_variables = sk.ContextVariables()
        clean_variables["believe"] = belief_text
        clean_variables["goal"] = goal
        clean_result = await self.kernel.run_async(
            clean_belief_semantic_function,
            input_vars=clean_variables
        )
        belief_text = clean_result.result.strip()

        relevant_function_manual = self.skills.get_available_function_skills()

        variables = sk.ContextVariables()

        variables["available_functions"] = relevant_function_manual
        variables["believe"] = belief_text
        variables["goal"] = goal

        semantic_function = self.kernel.create_semantic_function(PROMPT_PLAN)

        result = await self.kernel.run_async(
            semantic_function,
            input_vars=variables,
        )

        plan_result_string = result.result.strip()

        # save to database   
        plan = Plan(goal=goal, subtask=plan_result_string)
        Plan.session.add(plan)
        Plan.session.commit()

        logger.debug("Finish Create new plan.")
        return plan_result_string

    async def show_plan(self) -> str:
        plan_list = Plan.get_all_plans()
        plan_text = ""
        for plan in plan_list:
            plan_text += str("-" + plan.goal + "\n")
        return plan_text
