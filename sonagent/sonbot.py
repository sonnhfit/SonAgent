import os
import logging
import traceback
from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
from math import isclose
from threading import Lock
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

from sonagent.mixins import LoggingMixin
from sonagent.enums.enums import State
from sonagent.enums.rpcmessagetype import RPCMessageType
from sonagent.rpc import RPCManager
from sonagent.skills.skills_manager import SkillsManager
from sonagent.persistence.belief_models import Belief
from sonagent.agent import Agent
from sonagent.persistence.models import init_db
from sonagent.rpc.schedule_worker import ScheduleProcess



logger = logging.getLogger(__name__)


class SonBot(LoggingMixin):
    def __init__(self, config: dict, args: Any = None) -> None:


        self.state = State.STOPPED
        self.agent_mode = "chat"
        
        self.args = args

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
        self.sp = ScheduleProcess()



        self.agent = Agent(memory_path=memory_url, skills=self.skills, config=self.config)
        self.rpc: RPCManager = RPCManager(self)

        # Set initial bot state from config
        initial_state = self.config.get('initial_state')

        self.state = State[initial_state.upper()] if initial_state else State.STOPPED

    async def chat(self, input: str) -> str:
        if self.agent_mode == "chat":
            return await self.agent.chat(input)
        else:
            return await self.agent.chat_code(input)
    
    async def get_mode(self) -> str:
        return self.agent_mode
    
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
        pass

    def process_stopped(self) -> None:
        """
        handle process stopped
        """
        pass

    def notify_status(self, msg: str, msg_type=RPCMessageType.STATUS) -> None:
        """
        Public method for users of this class (worker, etc.) to send notifications
        via RPC about changes in the bot status.
        """
        self.rpc.send_msg({
            'type': msg_type,
            'status': msg
        })

