from typing import Literal, TypedDict, Union

from sonagent.enums import RPCMessageType


class RPCSendMsgBase(TypedDict):
    pass
    # ty1pe: Literal[RPCMessageType]


class RPCStatusMsg(RPCSendMsgBase):
    """Used for Status, Startup and Warning messages"""
    type: Literal[RPCMessageType.CHAT, RPCMessageType.STATUS, RPCMessageType.STARTUP, RPCMessageType.WARNING]
    status: str


RPCSendMsg = Union[
    RPCStatusMsg,
    RPCSendMsgBase
    ]
