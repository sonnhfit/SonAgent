from enum import Enum


class Stimulus(Enum):

    PLANNING = 'planning'
    CODING = 'coding'
    CHATTING = 'chatting'
    ASKING = 'asking'
    SCHEDULING = 'scheduling'
    SUMMARIZING = 'summarizing'
    CLEAN_BELIEF = 'clean_belief'
    HEARTBEAT = 'heartbeat'

    def __str__(self):
        return f"{self.name.lower()}"
