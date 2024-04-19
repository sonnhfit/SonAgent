from sonagent.nerve_system.language_area.llm_brain import LLMBrain
from openai import OpenAI
import os


class GPTLlmBrain(LLMBrain):
    def __init__(self):
        super().__init__()

    def infer(self, prompt, system_prompt=None, model="gpt-3.5-turbo"):
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
