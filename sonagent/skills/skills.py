
import logging
from abc import ABC, abstractmethod



class GSkill(ABC):
    plan = [
    ]

    plan_runable_obj = []

    def load(self, skills: dict = {}) -> None:
        for sub_task in self.plan:
            sub_t = sub_task
            if sub_task["function"] in skills:
                sub_t['func'] = skills[sub_task["function"]]
            self.plan_runable_obj.append(sub_t)

    def run(self, *args, **kwargs):
        output_result = []
        pre_params = None
        for i, sub_task in enumerate(self.plan_runable_obj):
            if "is_gskill" in sub_task:
                if sub_task["is_gskill"]:
                    if i ==  0:
                        pre_params = sub_task['func'].run(**sub_task.get('args', {}))
                    else:
                        pre_params = sub_task['func'].run(pre_params, **sub_task.get('args', {}))
            if i ==  0:
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

