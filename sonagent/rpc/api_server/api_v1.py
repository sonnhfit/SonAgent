import logging
from copy import deepcopy
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException

from sonagent import __version__

from sonagent.exceptions import OperationalException
from sonagent.rpc import RPC

from sonagent.rpc.rpc import RPCException
from sonagent.rpc.api_server.api_models import (Ping, Version, ChatMsg)
from sonagent.rpc.api_server.utils import get_rpc


logger = logging.getLogger(__name__)


API_VERSION = 2.34

# Public API, requires no auth.
router_public = APIRouter()
# Private API, protected by authentication
router = APIRouter()


@router_public.get('/ping', response_model=Ping)
def ping():
    """simple ping"""
    return {"status": "pong"}


@router_public.get('/version', response_model=Version, tags=['info'])
def version():
    """ Bot Version info"""
    return {"version": __version__}


@router_public.post('/chat', response_model=ChatMsg, tags=['chat'])
async def chat(msg: str, rpc: RPC = Depends(get_rpc)):
    message = await rpc.chat(msg)
    return {"message": message}

