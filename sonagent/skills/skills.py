
import logging
from abc import ABC, abstractmethod


class GSkill(ABC):

    def __init__(self, plan: list = [], skills: list = {}, gskills: list =  {}):
        self.plan = plan
        self.skills = skills
        self.gskills = gskills

        self.plan_runable_obj = []
        self.load(skills, gskills)

    def load(self, skills: dict = {}, gskills: dict = {}) -> None:
        for sub_task in self.plan:
            sub_t = sub_task
            if sub_task["function"] in skills:
                sub_t['func'] = skills[sub_task["function"]]
            if sub_task["function"] in gskills:
                if "is_gskill" in sub_task:
                    print(gskills[sub_task["function"]].run)
                    sub_t['func'] = gskills[sub_task["function"]].run
            self.plan_runable_obj.append(sub_t)

    def set_plan(self, plan: list) -> None:
        self.plan = plan

    def get_plan(self) -> list:
        return self.plan

    def reload_skills(self, plan: list=[], skills: dict={}, gskills: dict={}) -> None:
        self.plan = plan
        self.skills = skills
        self.gskills = gskills
        self.plan_runable_obj = []
        self.load(skills, gskills)
        
    def run(self, *args, **kwargs):
        output_result = []
        pre_params = None
        for i, sub_task in enumerate(self.plan_runable_obj):
            if "is_gskill" in sub_task:
                if sub_task["is_gskill"]:
                    if i == 0:
                        pre_params = sub_task['func'](**sub_task.get('args', {}))
                    else:
                        pre_params = sub_task['func'](pre_params, **sub_task.get('args', {}))
            else:
                if i == 0:
                    pre_params = sub_task['func'](**sub_task.get('args', {}))
                    output_result.append(
                        {
                            sub_task['function']: pre_params, 
                            'step': i,
                            'args': sub_task.get('args', {})
                        }
                    )
                else:
                    args_param = sub_task.get('args', {})
                    flag_run_pre = False
                    print(sub_task)
                    if "pre_pram" in sub_task:
                        if sub_task['pre_pram'] == True:
                            flag_run_pre = True
                            pre_params = sub_task['func'](pre_params, **args_param)
                    if not flag_run_pre:
                        pre_params = sub_task['func'](**args_param)
                        print(pre_params)
                        
                    output_result.append(
                        {
                            sub_task['function']: pre_params,
                            'step': i,
                            'args': args_param
                        }
                    )
            self.output_result = output_result
