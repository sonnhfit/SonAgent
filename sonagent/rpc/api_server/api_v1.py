import logging

from fastapi import APIRouter, Depends

from sonagent import __version__
from sonagent.rpc import RPC
from sonagent.rpc.api_server.api_models import ChatMsg, Ping, Version
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

