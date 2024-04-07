"""
This module contains class to define a RPC communications
"""
from abc import abstractmethod

from sonagent.constants import AGENT_MODE
from sonagent.rpc.rpc_types import RPCSendMsg


class RPCException(Exception):
    """
    Should be raised with a rpc-formatted message in an _rpc_* method
    if the required state is wrong, i.e.:

    raise RPCException('*Status:* `no active trade`')
    """

    def __init__(self, message: str) -> None:
        super().__init__(self)
        self.message = message

    def __str__(self):
        return self.message

    def __json__(self):
        return {
            'msg': self.message
        }


class RPCHandler:

    def __init__(self, rpc: 'RPC', config: dict) -> None:
        """
        Initializes RPCHandlers
        :param rpc: instance of RPC Helper class
        :param config: Configuration object
        :return: None
        """
        self._rpc = rpc
        self._config: dict = config

    @property
    def name(self) -> str:
        """ Returns the lowercase name of the implementation """
        return self.__class__.__name__.lower()

    @abstractmethod
    def cleanup(self) -> None:
        """ Cleanup pending module resources """

    @abstractmethod
    def send_msg(self, msg: RPCSendMsg) -> None:
        """ Sends a message to all registered rpc modules """


class RPC:
    def __init__(self, sonagent) -> None:
        """
        Initializes all enabled rpc modules
        :param freqtrade: Instance of a freqtrade bot
        :return: None
        """
        self.sonagent = sonagent
        self._config: dict = sonagent.config

    async def chat(self, msg: str) -> None:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.chat(msg)
    
    async def ibelieve(self, msg: str) -> bool:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        is_belief_added = await self.sonagent.ibelieve(msg)
        if is_belief_added:
            return "Belief added"
    
        return "Belief not added"

    async def reincarnate(self) -> None:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.reincarnate()
    
    async def askme(self, msg: str) -> str:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.askme(msg)

    async def clear_short_term_memory(self) -> str:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.clear_short_term_memory()
    
    async def planning(self, msg: str) -> str:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.planning(msg)
    
    async def show_plan(self) -> str:
        """
        Send a chat message to all registered rpc modules.
        :param msg: Message to send
        :return: None
        """
        return await self.sonagent.show_plan()
    
    async def show_mode(self) -> str:
        return self.sonagent.agent_mode
    
    async def show_skills(self) -> str:
        return self.sonagent.show_skills()
    
    async def show_schedule(self) -> str:
        return await self.sonagent.show_schedule()
    
    async def reload_skills(self) -> str:
        return self.sonagent.reload_skills()
    
    async def remove_skill(self, skill_name: str) -> str:
        return await self.sonagent.remove_skill(skill_name)
    
    async def mode(self, mode: str) -> str:
        if mode in AGENT_MODE:
            self.sonagent.agent_mode = mode
            return f"set agent mode is {mode}"
        return f'not done: agent mode is not validate ({str(AGENT_MODE)})'
    
    async def summerize_dialog(self) -> str:
        return self.sonagent.agent.short_term_memory.summerize_dialog()
