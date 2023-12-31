import logging
from sonagent.agent import Agent
import asyncio

logging.basicConfig(level=logging.INFO)

# Agent(memory_path="./user_data/memory").run(input="hello")
agent = Agent(memory_path="./user_data/memory")
# agent.create_belief(text="I prefer using PyTorch for training neural network", description="I believe that using PyTorch for training a neural network makes the source code cleaner and more readable. Therefore, I prefer using PyTorch for this task.")
# agent.sync_beliefs()


asyncio.run(agent.run(
    input="train neural network for image classification"
))
