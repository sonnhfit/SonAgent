import os
from openai import OpenAI
from sonagent.llm.prompt import summary_doc

def text_summary(docs):
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    sum_prompt = summary_doc(docs)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "play as interactive role, tell user if there is anything else you should take into consideration with the piece of text user trying to learn about. ",
            },
            {"role": "user", "content": sum_prompt},
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    return response.choices[0].message.content
