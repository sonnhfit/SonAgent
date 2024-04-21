import json
import logging
import os
from datetime import datetime

import yaml
from croniter import croniter
from openai import OpenAI

from sonagent.nerve_system import Brain
from sonagent.nerve_system.memory_area import ShortTermMemory, SonMemory
from sonagent.nerve_system.stimulus import Stimulus
from sonagent.persistence import Belief, Environment, Plan, ScheduleJob
from sonagent.tools import GitManager, LocalCodeManager
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, memory_path, skills, config: dict) -> None:
        # memory

        self.config = config

        logger.debug(f"Init memory with path {memory_path}.")

        # get memory config
        memory_config = self.config.get("vector_memory")
        self.memory = SonMemory(
            collection_name=memory_config.get("collection", "son_memory"),
            memory_type=memory_config.get("type", "file"),
            embedding_type=memory_config.get("embedding_type", "openai"),
            default_memory_path=memory_path,
            host=memory_config.get("host", "localhost"),
            port=memory_config.get("port", 8000),
        )
        
        llm_config = self.config.get('llm')
        self.brain = Brain(llm_config=llm_config)

        # self.sync_beliefs()

        self.skills = skills

        logger.info("--------- Start skill.---------")
        self.skills.start_skill(memory=self.memory)
        self.skills_dict = {}
        logger.info("--------- Start Done.---------")

        self.short_term_memory = ShortTermMemory(
            collection_name="short_term_memory", default_memory_path=memory_path
        )

        # git manager
        github = self.config.get("github")
        if github.get("enabled"):
            self.git_manager = GitManager(
                username=github.get("username"),
                repo_name=github.get("repo_name"),
                token=github.get("token"),
                local_repo_path=github.get("local_repo_path"),
            )
        else:
            self.git_manager = LocalCodeManager(
                local_repo_path=self.config.get("user_data_dir")
            )

        # load skill dict
        self.init_skills_dict()

    def remove_skill(self, skill_name):
        # remove skill_name from yaml

        skill_file_path = f"{self.git_manager.local_repo_path}/skills/skills.yaml"

        with open(skill_file_path, "r") as file:
            skills_register = yaml.safe_load(file)
        try:
            skills_register["skills"].remove(skill_name)
        except Exception as e:
            return f"skill doesn't exist: {e}"

        with open(skill_file_path, "w") as file:
            yaml.dump(skills_register, file)

        # reload skill
        self.reload_skills()

        return f"Remove skill {skill_name} successfully."

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

    def sync_beliefs(self) -> None:
        logger.debug("Start syncing beliefs to memory.")
        list_belief = Belief.get_all_belief()

        for belief in list_belief:
            self.memory.add(
                belief.text,
                {"description": belief.description},
                str(belief.id),
                collection_name="belief_base",
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
    
    async def show_env(self) -> list:
        env_list = Environment.get_all_environment()
        result = []
        for env in env_list:
            result.append([env.key, env.value[:10], env.description[:10]])
        return result

    async def remove_env(self, key: str) -> str:
        env = Environment.session.query(Environment).filter_by(key=key).first()
        if env is None:
            return f"Key {key} not found."
        Environment.session.delete(env)
        Environment.session.commit()
        return f"Key {key} removed successfully."
    
    async def add_env(self, key: str, value: str, description: str) -> str:
        env = Environment(key=key, value=value, description=description)
        Environment.session.add(env)
        Environment.session.commit()
        return f"Key {key} added successfully."
    
    async def excute_plan_task(self, task: dict) -> str:
        task_intance = str(task["function"]).split(".")
        if len(task_intance) < 2:
            return "Error: function name is not valid."
        class_name = task_intance[0]
        function_name = task_intance[1]
        task_func = getattr(self.skills_dict[class_name], function_name)
        logger.info(f"task_func: {task}")
        if "args" in task.keys():
            result = task_func(**task["args"])
        else:
            result = task_func()
        return result

    def excute_subtask(self, task: dict) -> str:
        task_intance = str(task["function"]).split(".")
        if len(task_intance) < 2:
            return "Error: function name is not valid."
        class_name = task_intance[0]
        function_name = task_intance[1]
        task_func = getattr(self.skills_dict[class_name], function_name)
        logger.info(f"task_func: {task}")
        if "args" in task.keys():
            result = task_func(**task["args"])
        else:
            result = task_func()
        return result

    def execute_plan(self, plan: dict) -> str:
        logger.info(f"execute plan: {plan}")
        tasks = plan.get("subtasks", [])
        result = ""
        for task in tasks:
            if task.get("function", "").startswith("unknow_"):
                continue
            result += str(self.excute_subtask(task))
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

    async def create_schedule_for_task_or_plan(self, goal_plan: str) -> str:
        plan_json = await self.planning(goal=goal_plan)

        # replace ```json to empty string
        plan_json = plan_json.replace("```json", "").replace("```", "")
        plan_json = json.loads(plan_json)
        logger.info(f"sk planner schedule json: {plan_json}")
        json_data_schedule = self.brain.language_brain.process(
            stimulus=Stimulus.SCHEDULING,
            goal=goal_plan
        )

        json_data_schedule = json_data_schedule.replace("```json", "").replace(
            "```", ""
        )
        schedule_plan_json = json.loads(json_data_schedule)
        logger.info(f"plan schedule json: {schedule_plan_json}")
        try:
            schedule_start_at = None
            schedule_end_at = None
            if len(schedule_plan_json["schedule_start_at"]) > 1:
                schedule_start_at = datetime.strptime(
                    schedule_plan_json["schedule_start_at"], "%Y-%m-%d %H:%M:%S"
                )

            if len(schedule_plan_json["schedule_end_at"]) > 1:
                schedule_end_at = datetime.strptime(
                    schedule_plan_json["schedule_end_at"], "%Y-%m-%d %H:%M:%S"
                )
            timenow = dt_now()

            cron = croniter(schedule_plan_json["schedule_interval"], timenow)
            next_run_at = cron.get_next(datetime)
            logger.info(
                f"Create schedule with next run is: {next_run_at} and timenow: {timenow}"
            )

            schedule_job = ScheduleJob(
                name=schedule_plan_json["name"],
                description=schedule_plan_json["description"],
                is_recurring=schedule_plan_json["is_recurring"],
                schedule_interval=schedule_plan_json["schedule_interval"],
                schedule_start_at=schedule_start_at,
                schedule_end_at=schedule_end_at,
                next_run_at=next_run_at,
                max_retry=3,
                plan=json.dumps(plan_json),
            )
            ScheduleJob.session.add(schedule_job)
            ScheduleJob.session.commit()
        except Exception as e:
            logger.error(f"Error create schedule job: {e}")
            return str(e)

        return "Schedule job created successfully."

    async def chat(self, input: str) -> str:

        belief = self.memory.search(collection_name="belief_base", query=input)

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
                {
                    "role": "system",
                    "content": "You are a virtual assistant with the ability to create plans for executing tasks using the create_plan_with_skills function if user need you do something. If the user's question falls outside the scope of the provided data.",
                }
            )
            logger.info(self.short_term_memory.get_chat_dialog())

        self.short_term_memory.add_chat_item({"role": "user", "content": input})
        message_text = self.short_term_memory.get_chat_dialog()

        custom_functions = [
            {
                "name": "create_plan_with_skills",
                "description": "run plan and compile code to done the task or requirement",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dialog_summary": {
                            "type": "string",
                            "description": "summary of the dialog keep that clear about how it works or steps to done the task",
                        }
                    },
                },
            },
            {
                "name": "create_schedule_for_task_or_plan",
                "description": "When a user needs to schedule a recurring task or an event, plan for a future time, they require a system that allows them to do so efficiently. This system should have the capability to set up recurring events if necessary and provide reminders if requested by the user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dialog_summary": {
                            "type": "string",
                            "description": "summary of the dialog keep that clear about schedule a recurring task or an event, time, provide reminders if requested by the user",
                        }
                    },
                },
            },
        ]

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=message_text,
            functions=custom_functions,
            function_call="auto",
            temperature=1,
            max_tokens=4096,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        r_str = str(response.choices[0].message.content)
        if r_str == "None":
            function_call_chat = response.choices[0].message.function_call
            name = function_call_chat.name

            if name == "create_plan_with_skills":
                logger.info(
                    f"***response.choices[0].message chat: {str(response.choices[0].message)}"
                )
                json_response = json.loads(
                    response.choices[0].message.function_call.arguments
                )
                r_str = await self.create_plan_and_running(
                    goal_plan=json_response.get("dialog_summary")
                )
            elif name == "create_schedule_for_task_or_plan":

                logger.info("run function create_schedule_for_task_or_plan")

                json_response = json.loads(
                    response.choices[0].message.function_call.arguments
                )
                r_str = await self.create_schedule_for_task_or_plan(
                    goal_plan=json_response.get("dialog_summary")
                )

        response = str(r_str)

        self.short_term_memory.add_chat_item(
            {"role": "assistant", "content": str(response)}
        )
        logger.info(f"Finish chat: {str(response)}")

        return str(response)

    async def chat_code(self, input: str) -> str:
        if len(self.short_term_memory.get_chat_dialog()) == 0:
            self.short_term_memory.add_chat_item(
                {
                    "role": "system",
                    "content": "you are a sennior software engineer, expert in python, Every time you generate code, plan, or the way to done task, ask the user if he wants to compile this code",
                }
            )

        self.short_term_memory.add_chat_item({"role": "user", "content": input})
        message_text = self.short_term_memory.get_chat_dialog()

        logger.info(f"Start chat: {message_text}")
        custom_functions = [
            {
                "name": "run_plan_and_compile_code",
                "description": "run plan and compile code to done the task or requirement",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary_plan_or_requirement": {
                            "type": "string",
                            "description": "summary of the plan or requirement keep that clear about how it works or steps to done the task",
                        }
                    },
                },
            }
        ]

        r_str, response = self.brain.language_brain.process(
            stimulus=Stimulus.CHAT_CODE,
            messages=message_text,
            custom_functions=custom_functions,
        )

        if str(r_str) == "None":

            r_str = "I send requirment to compile code agent. Please wait for a moment."
            function_call_chat = response.choices[0].message.function_call
            name = function_call_chat.name
            json_response = json.loads(
                response.choices[0].message.function_call.arguments
            )
            print("---------------------------")
            print(json_response)

            if name == "run_plan_and_compile_code":
                summary_plan_or_requirement = json_response.get(
                    "summary_plan_or_requirement"
                )

                self.brain.language_brain.process(
                    stimulus=Stimulus.CODING,
                    git_manager=self.git_manager,
                    user_data_dir=self.config.get("user_data_dir", None),
                    summary_plan_or_requirement=summary_plan_or_requirement
                )

        self.short_term_memory.add_chat_item({"role": "assistant", "content": r_str})
        logger.info(f"Finish with chat return: {r_str}")
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

        belief = self.memory.search(collection_name="belief_base", query=question)

        belief_ids = belief["ids"][0]

        logger.debug(f"belief_ids: {belief_ids}")

        result_list = self.get_beliefs_for_planner(belief_ids)

        logger.debug(f"result_list: {result_list}")

        belief_text = ""
        for item in result_list:
            belief_text += str("-" + item.text + "\n")

        logger.info(f"Belief_text: \n{belief_text}")

        result = self.brain.language_brain.process(
            stimulus=Stimulus.ASKING, believe=belief_text, question=question
        )

        logger.debug("Finish asking.")
        return str(result)

    async def reincarnate(self) -> str:
        if self.delete_everything():
            return "Reincarnate successfully."
        else:
            return "Reincarnate failed."

    async def planning(self, goal: str) -> str:

        belief = self.memory.search(collection_name="belief_base", query=goal)
        belief_ids = belief["ids"][0]
        result_list = self.get_beliefs_for_planner(belief_ids)

        belief_text = ""
        for item in result_list:
            belief_text += str("-" + item.text + "\n")

        # clean belief
        clean_result = self.brain.language_brain.process(
            stimulus=Stimulus.CLEAN_BELIEF, believe=belief_text, goal=goal
        )

        belief_text = clean_result.strip()

        relevant_function_manual = self.skills.get_available_function_skills(
            goal, self.memory
        )

        logger.info(f"available_functions {relevant_function_manual}")

        result = self.brain.language_brain.process(
            stimulus=Stimulus.PLANNING,
            believe=belief_text,
            goal=goal,
            available_functions=relevant_function_manual
        )
        plan_result_string = result.strip()

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

    async def show_schedule(self) -> str:
        schedule_jobs = ScheduleJob.get_all_schedule_not_completed_jobs()
        schedule_text = ""
        for job in schedule_jobs:
            schedule_text += "-----------------\n"
            schedule_text += f"**Task**: **{job.name}** \n"
            schedule_text += f"Description: {job.description}\n"
            schedule_text += f"Plan: {job.plan}\n"
            schedule_text += f"Recurrence: {job.is_recurring}\n\n"

        return schedule_text
