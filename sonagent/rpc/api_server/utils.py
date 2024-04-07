from typing import AsyncIterator, Optional

from sonagent.rpc.rpc import RPC, RPCException

from .webserver import ApiServer


def get_rpc_optional() -> Optional[RPC]:
    if ApiServer._has_rpc:
        return ApiServer._rpc
    return None


async def get_rpc() -> Optional[AsyncIterator[RPC]]:

    _rpc = get_rpc_optional()
    if _rpc:
        try:
            yield _rpc
        finally:
            pass
    else:
        raise RPCException('Bot is not in the correct state')

