from typing import Literal, Optional, TypedDict, Union

from sonagent.enums import RPCMessageType


class RPCSendMsgBase(TypedDict):
    pass
    # ty1pe: Literal[RPCMessageType]


class RPCStatusMsg(RPCSendMsgBase):
    """Used for Status, Startup and Warning messages"""
    type: Literal[RPCMessageType.CHAT, RPCMessageType.STATUS, RPCMessageType.STARTUP, RPCMessageType.WARNING]
    status: str


class RPCImageMsg(RPCSendMsgBase):
    """Used for sending image messages"""
    type: Literal[RPCMessageType.IMAGE]
    image_url: str
    caption: Optional[str] = None


RPCSendMsg = Union[
    RPCStatusMsg,
    RPCImageMsg,
    RPCSendMsgBase
    ]