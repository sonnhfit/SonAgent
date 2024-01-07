from enum import Enum


class RPCMessageType(str, Enum):
    STATUS = 'status'
    WARNING = 'warning'
    EXCEPTION = 'exception'
    STARTUP = 'startup'

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value