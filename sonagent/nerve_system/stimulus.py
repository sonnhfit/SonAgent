from enum import Enum


class Stimulus(Enum):

    PLANNING = 'planning'
    CODING = 'coding'
    CHAT_CODE = 'chat_code'
    REWRITE_CODE = 'rewrite_code'
    CREATE_SKILL_DOCS = 'create_skill_docs'
    WRITE_DOCS = 'write_docs'
    WRITE_GITHUB_METADATA = 'write_github_metadata'
    CHATTING = 'chatting'
    ASKING = 'asking'
    SCHEDULING = 'scheduling'
    SUMMARIZING = 'summarizing'
    CLEAN_BELIEF = 'clean_belief'
    HEARTBEAT = 'heartbeat'

    def __str__(self):
        return f"{self.name.lower()}"
