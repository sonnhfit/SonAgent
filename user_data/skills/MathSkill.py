"""
A skill for basic math operations
"""

from pydantic import BaseModel
from sonagent.rpc import IOMsg


class MathSkill(BaseModel):
    '''
    MathSkill.add
    description: Add two numbers
    args:
        - a: First number
        - b: Second number
    '''
    
    def add(self, a: float, b: float) -> str:
        result = a + b
        msg = f"Result: {a} + {b} = {result}"
        IOMsg.send_msg(msg)
        return msg
