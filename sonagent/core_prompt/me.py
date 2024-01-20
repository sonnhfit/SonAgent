ASK_ABOUT_ME_PROMP = """
This is what I believe is true. Please rely on it to answer the following question.
answer in the language of the person asking the question

[believe]
- i like eating apples
- i think apple is good for health

Q: do you want to drink apple juice?
A: yes maybe i will try that


[believe]
- i like go shopping with my friends
- i want to go a big shopping mall

Q: do you want to go shopping with me?
A: yes i want to go shopping with you

[believe]
{{$believe}}

Q: {{$question}}
A:
"""
