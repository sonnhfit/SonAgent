import logging
from copy import deepcopy
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException

from sonagent import __version__

from sonagent.exceptions import OperationalException
from sonagent.rpc import RPC

from sonagent.rpc.rpc import RPCException
from sonagent.rpc.api_server.api_models import (Ping, Version)

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


@router.get('/version', response_model=Version, tags=['info'])
def version():
    """ Bot Version info"""
    return {"version": __version__}

