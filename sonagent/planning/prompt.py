PROMPT_PLAN = """
You are a planner for the Agent.
Your job is to create a properly formatted JSON plan step by step, to satisfy the goal given with 
the things you believe to be the best..
Create a list of subtasks based off the [GOAL] provided.
Each subtask must be from within the [AVAILABLE FUNCTIONS] list. Do not use any functions that are not in the list.
Base your decisions on which functions to use from the description and the name of the function.
Sometimes, a function may take arguments. Provide them if necessary.
The plan should be as short as possible. If you dont have available functions to satisfy the goal, Please name that function with the prefix `unknow_[function_name]`.

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
"Tell a joke about cars at 9h am everyday. Translate it to Spanish"

[BELIEVE]
- cars can be used to transport people
- cars can be used to fly around the world
- cars can be used to go to the moon

[OUTPUT]
    {
        "input": "cars",
        "subtasks": [
            {"function": "FunSkill.Joke", "description": "Generate a funny joke about cars"},
            {"function": "WriterSkill.Translate", "args": {"language": "Spanish"}, "description": "Translate the joke to Spanish"}
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

[GOAL]
"Tomorrow is Valentine's day. I need to come up with a few date ideas.
She likes Edgar Allen Poe so write using his style.
E-mail these ideas to my significant other. Translate it to French."

[OUTPUT]
    {
        "input": "Valentine's Day Date Ideas",
        "subtasks": [
            {"function": "WriterSkill.Brainstorm", "description": "Brainstorm ideas for Valentine's Day"},
            {"function": "EdgarAllenPoeSkill.Poe", "description": "Write in the style of Edgar Allen Poe"},
            {"function": "WriterSkill.EmailTo", "args": {"recipient": "significant_other"}, "description": "Email the ideas to my significant other"},
            {"function": "unknow_WriterSkill.Translate", "args": {"language": "French"}, description: "Translate the ideas to French"}
        ]
    }


[AVAILABLE FUNCTIONS]
{{$available_functions}}

[GOAL]
{{$goal}}

[BELIEVE]
{{$believe}}

[OUTPUT]
"""


SEQUENCE_PLAN = """
Create an XML plan step by step, to satisfy the goal given, 
with the available functions and When creating a plan, prioritize your beliefs first. If it cannot help you achieve your goals, then use other methods..

[AVAILABLE FUNCTIONS]

{{$available_functions}}

[END AVAILABLE FUNCTIONS]

[BELIEVE]
{{$believe}}
[END BELIEVE]

To create a plan, follow these steps:
0. The plan should be as short as possible.
1. From a <goal> create a <plan> as a series of <functions>.
2. A plan has 'INPUT' available in context variables by default.
3. Before using any function in a plan, check that it is present in the [AVAILABLE FUNCTIONS] list. If it is not, do not use it.
4. Only use functions that are required for the given goal.
5. Append an "END" XML comment at the end of the plan after the final closing </plan> tag.
6. Always output valid XML that can be parsed by an XML parser.
7. If a plan cannot be created with the [AVAILABLE FUNCTIONS], return <plan />.

All plans take the form of:
<plan>
    <!-- ... reason for taking step ... -->
    <function.{FullyQualifiedFunctionName} ... />
    <!-- ... reason for taking step ... -->
    <function.{FullyQualifiedFunctionName} ... />
    <!-- ... reason for taking step ... -->
    <function.{FullyQualifiedFunctionName} ... />
    (... etc ...)
</plan>
<!-- END -->

To call a function, follow these steps:
1. A function has one or more named parameters and a single 'output' which are all strings. Parameter values should be xml escaped.
2. To save an 'output' from a <function>, to pass into a future <function>, use <function.{FullyQualifiedFunctionName} ... setContextVariable="<UNIQUE_VARIABLE_KEY>"/>
3. To save an 'output' from a <function>, to return as part of a plan result, use <function.{FullyQualifiedFunctionName} ... appendToResult="RESULT__<UNIQUE_RESULT_KEY>"/>
4. Use a '$' to reference a context variable in a parameter, e.g. when `INPUT='world'` the parameter 'Hello $INPUT' will evaluate to `Hello world`.
5. Functions do not have access to the context variables of other functions. Do not attempt to use context variables as arrays or objects. Instead, use available functions to extract specific elements or properties from context variables.

DO NOT DO THIS, THE PARAMETER VALUE IS NOT XML ESCAPED:
<function.Name4 input="$SOME_PREVIOUS_OUTPUT" parameter_name="some value with a <!-- 'comment' in it-->"/>

DO NOT DO THIS, THE PARAMETER VALUE IS ATTEMPTING TO USE A CONTEXT VARIABLE AS AN ARRAY/OBJECT:
<function.CallFunction input="$OTHER_OUTPUT[1]"/>

Here is a valid example of how to call a function "_Function_.Name" with a single input and save its output:
<function._Function_.Name input="this is my input" setContextVariable="SOME_KEY"/>

Here is a valid example of how to call a function "FunctionName2" with a single input and return its output as part of the plan result:
<function.FunctionName2 input="Hello $INPUT" appendToResult="RESULT__FINAL_ANSWER"/>

Here is a valid example of how to call a function "Name3" with multiple inputs:
<function.Name3 input="$SOME_PREVIOUS_OUTPUT" parameter_name="some value with a &lt;!-- &apos;comment&apos; in it--&gt;"/>

Begin!

<goal>{{$input}}</goal>
"""


CLEAN_BELIEF_PROMPT = """
List the beliefs related to achieving your goals and eliminate the remaining beliefs
[BELIEVE]
- Earth orbits the sun
- The sun is a star
- The sun is a ball of fire
- The sun is a source of light
- The sun is a source of energy
- A tree is a plant

[GOAL]
- Calculate the orbits of the planets

[OUTPUT]
- Earth orbits the sun
- The sun is a star
- The sun is a ball of fire
- The sun is a source of light
- The sun is a source of energy


[BELIEVE]
{{$belief}}
[GOAL]
{{$goal}}

[OUTPUT]

"""
