import logging
import os

from openai import OpenAI

from sonagent.nerve_system.language_area.llm_brain import LLMBrain

logger = logging.getLogger(__name__)


class GPTLlmBrain(LLMBrain):
    def __init__(self):
        super().__init__()

    def infer(
        self, prompt=None,
        system_prompt=None, model="gpt-3.5-turbo", custom_functions=None
    ):
        logger.info(f"Infer LLM with prompt: {prompt}")
        if system_prompt:
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": prompt},
            ]
        else:
            messages = [{"role": "user", "content": prompt}]

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        if custom_functions:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                functions=custom_functions,
                function_call="auto",
                temperature=1,
                max_tokens=2048,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            return response.choices[0].message.content, response
        else:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=1,
                max_tokens=2048,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )

        return response.choices[0].message.content

    def chat_infer(
        self, messages,
        model="gpt-3.5-turbo",
        custom_functions=None
    ):
        logger.info(f"Infer LLM with messages: {messages}")
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        if custom_functions:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                functions=custom_functions,
                function_call="auto",
                temperature=1,
                max_tokens=2048,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            return response.choices[0].message.content, response
        else:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=1,
                max_tokens=2048,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            return response.choices[0].message.content

