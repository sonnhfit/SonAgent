import os
import logging
import json
import yaml
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
from sonagent.tools import GitManager, LocalCodeManager
from openai import OpenAI

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, memory_path, skills, config: dict) -> None:
        # memory
        logger.debug(f"init memory with path {memory_path}.")
        self.memory = SonMemory(default_memory_path=memory_path)

        self.config = config

        # planner
        self.planner = SonAgentPlanner()
        # self.sync_beliefs()

        self.skills = skills

        logger.info("--------- Start skill.---------")
        self.skills.start_skill(memory=self.memory)
        self.skills_dict = {}
        logger.info("--------- Start Done.---------")


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

        self.short_term_memory = ShortTermMemory(
            collection_name="short_term_memory", default_memory_path=memory_path
        )

        # print(deployment, api_key, endpoint)
        self.kernel = sk.Kernel()
        
        self.kernel.add_chat_service(
            "chat_completion",
            self.chat_service
        )

        # git manager
        github = self.config.get('github')
        if github.get('enabled'):
            self.git_manager = GitManager(
                username=github.get('username'),
                repo_name=github.get('repo_name'),
                token=github.get('token'),
                local_repo_path=github.get('local_repo_path')
            )
        else:
            self.git_manager = LocalCodeManager(local_repo_path=self.config.get('user_data_dir'))
        
        if self.git_manager is not None:
            user_data_dir = self.config.get('user_data_dir')
            self.codeagent = SonCodeAgent(
                git_manager=self.git_manager, user_data_dir=user_data_dir
            )
        else:
            self.codeagent = SonCodeAgent()

        # load skill dict 
        self.init_skills_dict()

    def remove_skill(self, skill_name):
        # remove skill_name from yaml 

        skill_file_path = f"{self.git_manager.local_repo_path}/skills/skills.yaml"

        with open(skill_file_path, 'r') as file:
            skills_register = yaml.safe_load(file)
        try:
            skills_register['skills'].remove(skill_name)
        except Exception as e:
            return f"skill doesn't exist: {e}"

        with open(skill_file_path, 'w') as file:
            yaml.dump(skills_register, file)
    

        # reload skill
        self.reload_skills()

        return f"Remove skill {skill_name} successfully."



    def save_function_to_memory(self, function_name: str) -> None:
        pass

    def init_skills_dict(self) -> None:
        for skill in self.skills.get_all_skills():
            self.skills_dict[str(skill.__class__.__name__)] = skill

    def get_beliefs_for_planner(self, ids: list) -> list:
        list_belief = Belief.get_belief_by_ids(ids=ids)
        return list_belief

    def show_skills(self) -> str:
        self.skills.reload_skills()
        return ", ".join(self.skills_dict.keys())

    def _reload_skills(self):
        logger.info("--------- reload skill.---------")
        self.skills.start_skill(memory=self.memory)
        self.skills_dict = {}
        self.init_skills_dict()

        logger.info("--------- reload Done.---------")

    def reload_skills(self) -> str:
        self._reload_skills()
        return self.show_skills()

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

    async def excute_plan_task(self, task: dict) -> str: 
        task_intance = str(task['function']).split('.')
        class_name = task_intance[0]
        function_name = task_intance[1]
        task_func = getattr(self.skills_dict[class_name], function_name)
        logger.info(f"task_func: {task}")
        if 'args' in task.keys():
            result = task_func(**task['args'])
        else:
            result = task_func()
        return result

    async def create_plan_and_running(self, goal_plan: str) -> str:
        plan_json = await self.planning(goal=goal_plan)

        # replace ```json to empty string
        plan_json = plan_json.replace("```json", "").replace("```", "")
        plan_json = json.loads(plan_json)

        logger.info(f"plan_json: {plan_json}")
        tasks = plan_json.get("subtasks", [])

        result = ""
        for task in tasks:
            result += str(await self.excute_plan_task(task))

        return result

    async def chat(self, input: str) -> str:

        belief = self.memory.brain_area_search(
            area_collection_name="belief_base", query=input
        )

        belief_ids = belief["ids"][0]

        logger.info(f"belief_ids: {belief_ids}")

        result_list = self.get_beliefs_for_planner(belief_ids)

        logger.info(f"result_list: {result_list}")

        belief_text = ""
        for item in result_list:
            belief_text += str("-" + item.text + "\n")
        
        logger.info(f"Belief_text: \n{belief_text}")
        if len(self.short_term_memory.get_chat_dialog()) == 0:
            self.short_term_memory.add_chat_item(
                {"role": "system", "content": f"You are a virtual assistant with the ability to create plans for executing tasks using the create_plan_with_skills function if user need you do something. If the user's question falls outside the scope of the provided data."}
            )
            logger.info(self.short_term_memory.get_chat_dialog())
        
        self.short_term_memory.add_chat_item({"role": "user", "content": input})
        message_text = self.short_term_memory.get_chat_dialog()

        custom_functions = [
            {
                'name': 'create_plan_with_skills',
                'description': 'run plan and compile code to done the task or requirement',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'dialog_summary': {
                            'type': 'string',
                            'description': 'summary of the dialog keep that clear about how it works or steps to done the task'
                        }
                    }
                }
            }
        ]

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=message_text,
            functions=custom_functions,
            function_call='auto',
            temperature=1,
            max_tokens=4096,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        r_str = str(response.choices[0].message.content)
        if r_str == "None":

            logger.info(f"***response.choices[0].message chat: {str(response.choices[0].message)}")
            json_response = json.loads(response.choices[0].message.function_call.arguments)
            r_str = await self.create_plan_and_running(goal_plan=json_response.get("dialog_summary"))
        
        response = str(r_str)
        
        self.short_term_memory.add_chat_item({"role":"assistant","content":str(response)})
        logger.info(f"Finish chat: {str(response)}")

        return str(response)

    async def chat_code(self, input: str) -> str:
        if len(self.short_term_memory.get_chat_dialog()) == 0:
            self.short_term_memory.add_chat_item(
                {"role": "system", "content": "you are a sennior software engineer, expert in python, Every time you generate code, plan, or the way to done task, ask the user if he wants to compile this code"}
            )

        self.short_term_memory.add_chat_item({"role": "user", "content": input})
        message_text = self.short_term_memory.get_chat_dialog()

        logger.info(f"Start chat: {message_text}")
        custom_functions = [
            {
                'name': 'run_plan_and_compile_code',
                'description': 'run plan and compile code to done the task or requirement',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'summary_plan_or_requirement': {
                            'type': 'string',
                            'description': 'summary of the plan or requirement keep that clear about how it works or steps to done the task'
                        }
                    }
                }
            }
        ]

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=message_text,
            functions=custom_functions,
            function_call='auto',
            temperature=1,
            max_tokens=4096,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        r_str = str(response.choices[0].message.content)
        if r_str == "None":

            r_str = "I send requirment to compile code agent. Please wait for a moment."
            function_call_chat = response.choices[0].message.function_call
            name = function_call_chat.name
            json_response = json.loads(response.choices[0].message.function_call.arguments)
            print("---------------------------")
            print(json_response)

            if name == "run_plan_and_compile_code":
                summary_plan_or_requirement = json_response.get("summary_plan_or_requirement")
                self.codeagent.gen_code(message=summary_plan_or_requirement, is_create_pull_request=True)

        print(response.choices[0].message.function_call)
        self.short_term_memory.add_chat_item(
            {"role":"assistant", "content": r_str}
        )
        logger.info(f"Finish chat: {str(response)}")

        return r_str
    
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

        relevant_function_manual = self.skills.get_available_function_skills(goal, self.memory)

        variables = sk.ContextVariables()

        variables["available_functions"] = relevant_function_manual
        variables["believe"] = ""
        variables["goal"] = goal

        logger.info(f"available_functions {relevant_function_manual}")

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
