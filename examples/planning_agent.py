import asyncio
import semantic_kernel as sk
from sonagent.planning.planner import SonAgentPlanner
from semantic_kernel.planning.basic_planner import BasicPlanner


async def main():
    kernel = sk.Kernel()
    planner = BasicPlanner()
    ask = "If my investment of 2130.23 dollars increased by 23%, how much would I have after I spent $5 on a latte?"
    # plan =  await planner.create_plan_async(ask, kernel)
    print("ok")

asyncio.run(main())