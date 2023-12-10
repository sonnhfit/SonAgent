# planning module 
from semantic_kernel.kernel import Kernel
from semantic_kernel.planning.basic_planner import Plan, BasicPlanner

PROMPT = """
You are a planner for the Semantic Kernel.
Your job is to create a properly formatted JSON plan step by step, to satisfy the goal given.
Create a list of subtasks based off the [GOAL] provided.
Each subtask must be from within the [AVAILABLE FUNCTIONS] list. Do not use any functions that are not in the list.
Base your decisions on which functions to use from the description and the name of the function.
Sometimes, a function may take arguments. Provide them if necessary.
The plan should be as short as possible.
For example:

[AVAILABLE FUNCTIONS]
EmailConnector.LookupContactEmail
description: looks up the a contact and retrieves their email address
args:
- name: the name to look up

WriterSkill.EmailTo
description: email the input text to a recipient
args:
- input: the text to email
- recipient: the recipient's email address. Multiple addresses may be included if separated by ';'.

WriterSkill.Translate
description: translate the input to another language
args:
- input: the text to translate
- language: the language to translate to

WriterSkill.Summarize
description: summarize input text
args:
- input: the text to summarize

FunSkill.Joke
description: Generate a funny joke
args:
- input: the input to generate a joke about

[GOAL]
"Tell a joke about cars. Translate it to Spanish"

[OUTPUT]
    {
        "input": "cars",
        "subtasks": [
            {"function": "FunSkill.Joke"},
            {"function": "WriterSkill.Translate", "args": {"language": "Spanish"}}
        ]
    }

[AVAILABLE FUNCTIONS]
WriterSkill.Brainstorm
description: Brainstorm ideas
args:
- input: the input to brainstorm about

EdgarAllenPoeSkill.Poe
description: Write in the style of author Edgar Allen Poe
args:
- input: the input to write about

WriterSkill.EmailTo
description: Write an email to a recipient
args:
- input: the input to write about
- recipient: the recipient's email address.

WriterSkill.Translate
description: translate the input to another language
args:
- input: the text to translate
- language: the language to translate to

[GOAL]
"Tomorrow is Valentine's day. I need to come up with a few date ideas.
She likes Edgar Allen Poe so write using his style.
E-mail these ideas to my significant other. Translate it to French."

[OUTPUT]
    {
        "input": "Valentine's Day Date Ideas",
        "subtasks": [
            {"function": "WriterSkill.Brainstorm"},
            {"function": "EdgarAllenPoeSkill.Poe"},
            {"function": "WriterSkill.EmailTo", "args": {"recipient": "significant_other"}},
            {"function": "WriterSkill.Translate", "args": {"language": "French"}}
        ]
    }

[AVAILABLE FUNCTIONS]
{{$available_functions}}

[GOAL]
{{$goal}}

[OUTPUT]
"""

  
class SonAgentPlanner(BasicPlanner):

    def create_plan_async(
        self,
        goal: str,
        kernel: Kernel,
        prompt: str = PROMPT,
    ) -> Plan:
        return super().create_plan_async(goal, kernel, prompt)

    def load_planning_prompt(self):
        pass

    def save_plan_to_db(self, plan):
        pass
