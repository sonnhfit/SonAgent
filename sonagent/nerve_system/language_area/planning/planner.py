# planning module 
from semantic_kernel.kernel import Kernel
from semantic_kernel.planning.basic_planner import BasicPlanner, Plan

import sonagent.nerve_system.language_area.prompt.planning as planning_prompt


class SonAgentPlanner(BasicPlanner):

    def create_plan_async(
        self,
        goal: str,
        kernel: Kernel,
        prompt: str = planning_prompt.PROMPT,
    ) -> Plan:
        return super().create_plan_async(goal, kernel, prompt)

