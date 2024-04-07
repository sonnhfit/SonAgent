import ast
import logging
import os
from datetime import datetime
from typing import Any

from croniter import croniter
from schedule import Scheduler

from sonagent.agent import Agent
from sonagent.enums.enums import State
from sonagent.enums.rpcmessagetype import RPCMessageType
from sonagent.mixins import LoggingMixin
from sonagent.persistence.belief_models import Belief
from sonagent.persistence.models import ScheduleJob, init_db
from sonagent.rpc import IOMsg, RPCManager
from sonagent.skills.skills_manager import SkillsManager
from sonagent.utils.datetime_helpers import dt_now

# import threading


logger = logging.getLogger(__name__)


class SonBot(LoggingMixin):
    def __init__(self, config: dict, args: Any = None) -> None:

        self.state = State.STOPPED
        self.agent_mode = "chat"
        
        self.args = args
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        self.config = config
        
        memory_url = self.args.get('memory-url', "user_data/memory")
        agentdb = self.args.get('agentdb', "sqlite:///user_data/agentdb.sqlite")

        # get openai key 
        openai = self.config.get('openai')
        if openai.get('api_type', None) == 'openai':
            os.environ["OPENAI_API_KEY"] = openai.get('api_key')
            print("----------------")

        if agentdb is None:
            agentdb = "sqlite:///user_data/agentdb.sqlite"
        
        if memory_url is None:
            memory_url = "./user_data/memory"
        try:
            init_db(agentdb)
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise e
        
        self.skills = SkillsManager(self)

        names = str(self.skills.load_register_skills_name())
        logger.info(f"SKILLLS NAME: {names}")
        self._schedule = Scheduler()

        self.agent = Agent(memory_path=memory_url, skills=self.skills, config=self.config)
        self.rpc: RPCManager = RPCManager(self)

        def update():
            self.update_schedule_jobs()
    
        self._schedule.every(15).seconds.do(update)

        # Set initial bot state from config
        initial_state = self.config.get('initial_state')

        self.state = State[initial_state.upper()] if initial_state else State.STOPPED
        
        IOMsg.rpc = self.rpc


    def update_schedule_jobs(self) -> None:
        """
        Update the schedule jobs for the bot
        :param jobs: List of jobs to update
        :return: None
        """
        # logger.info('Updating schedule jobs ...')
        # get job for run now 
        job_list = ScheduleJob.get_job_with_next_run_at_now()
        if job_list and len(job_list) > 0:
            logger.info(f"Found {len(job_list)} jobs to run now")
            for job in job_list:
                # job.run()
                job_dict = ast.literal_eval(job.plan)
                self.agent.execute_plan(job_dict)
                if job.is_recurring:
                    cron_expression = job.schedule_interval

                    cron = croniter(cron_expression, dt_now())
                    cron_time = cron.get_next(datetime)
                    job.last_run_at = job.next_run_at
                    job.next_run_at = cron_time
                    job.status = "pending"
                    ScheduleJob.session.commit()
                else:
                    job.status = "completed"
                    job.last_run_at = job.next_run_at
                    ScheduleJob.session.commit()
    
    async def chat(self, input: str) -> str:
        if self.agent_mode == "chat":

            chat = await self.agent.chat(input)
            try:
                self.notify_chat_event(chat)
            except Exception as e:
                logger.error(f"Error notifying chat event: {e}")
            return chat
        else:
            return await self.agent.chat_code(input)
    
    async def get_mode(self) -> str:
        return self.agent_mode
    
    async def remove_skill(self, skill_name: str) -> str:
        result = self.agent.remove_skill(skill_name)
        self.reload_skills()
        return result
    
    async def change_agent_mode(self, mode: str) -> str:
        self.agent_mode = mode
        return f"Agent mode changed to {mode}"
    
    async def ibelieve(self, input: str) -> str:
        return await self.agent.ibelieve(input)

    async def reincarnate(self) -> str:
        return await self.agent.reincarnate()
    
    async def askme(self, input: str) -> str:
        return await self.agent.askme(input)
    
    async def clear_short_term_memory(self) -> str:
        return await self.agent.clear_short_term_memory()

    async def planning(self, goal: str) -> str:
        return await self.agent.planning(goal)

    async def show_plan(self) -> str:
        return await self.agent.show_plan()
    
    async def show_schedule(self) -> str:
        return await self.agent.show_schedule()
    
    def show_skills(self) -> str:
        return self.agent.show_skills()
    
    def reload_skills(self) -> str:
        return self.agent.reload_skills()
    
    def cleanup(self) -> None:
        """
        Cleanup pending resources on an already stopped bot
        :return: None
        """
        logger.info('Cleaning up modules ...')
        try:
            # Wrap db activities in shutdown to avoid problems if database is gone,
            # and raises further exceptions.
            logger.info('Cleaning up process ...')
        except Exception as e:
            logger.warning(f'Exception during cleanup: {e.__class__.__name__} {e}')

        # finally:
        #     self.strategy.ft_bot_cleanup()

        # RPC cleanup 
        # self.rpc.cleanup()
        # if self.emc:
        #     self.emc.shutdown()

        # commit all changes to the database
        try:
            Belief.session.commit()
        except Exception:
            # Exeptions here will be happening if the db disappeared.
            # At which point we can no longer commit anyway.
            pass

    def startup(self) -> None:
        pass

    def process(self) -> None:
        # print("process")
        self._schedule.run_pending()

    def process_stopped(self) -> None:
        """
        handle process stopped
        """
        pass

    def notify_chat_event(self, msg: str, msg_type=RPCMessageType.CHAT) -> None:
        self.rpc.send_msg({
            'type': msg_type,
            'message': msg
        })


    def notify_status(self, msg: str, msg_type=RPCMessageType.STATUS) -> None:
        """
        Public method for users of this class (worker, etc.) to send notifications
        via RPC about changes in the bot status.
        """
        self.rpc.send_msg({
            'type': msg_type,
            'status': msg
        })