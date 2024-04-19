from abc import abstractmethod
from sonagent.nerve_system.brain_lobe import BrainLobe
from sonagent.nerve_system.stimulus import Stimulus
import sonagent.nerve_system.language_area.prompt.me as me_prompt
import sonagent.nerve_system.language_area.prompt.schedule as schedule_prompt
import sonagent.nerve_system.language_area.prompt.planning as planning_prompt


class LLMBrain(BrainLobe):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def infer(self, prompt, system_prompt=None, model="gpt-3.5-turbo"):
        raise NotImplementedError

    def process(self, stimulus, **kwargs):
        if stimulus == Stimulus.ASKING:
            # get prompt from kwargs
            prompt = me_prompt.ASK_ABOUT_ME_PROMPT.format(
                believe=kwargs.get("believe", ""),
                question=kwargs.get("question", ""),
            )
            result = self.infer(prompt)

        elif stimulus == Stimulus.SCHEDULING:
            prompt = schedule_prompt.AUTO_SCHEDULE_PROMPT.format(
                goal=kwargs.get("goal", ""),
            )
            system_prompt = schedule_prompt.SYSTEM_PROMPT
            result = self.infer(prompt, system_prompt)

        elif stimulus == Stimulus.PLANNING:
            prompt = planning_prompt.PROMPT_PLAN.format(
                believe=kwargs.get("believe", ""),
                goal=kwargs.get("goal", ""),
                available_functions=kwargs.get("available_functions", "")
            )
            result = self.infer(prompt)
        elif stimulus == Stimulus.CLEAN_BELIEF:
            prompt = planning_prompt.CLEAN_BELIEF_PROMPT.format(
                goal=kwargs.get("goal", ""),
                believe=kwargs.get("believe", ""),
            )
            result = self.infer(prompt)
        elif stimulus == Stimulus.CODING:
            pass

        elif stimulus == Stimulus.SUMMARIZING:
            pass

        return result

    def planning(self, stimulus):
        return stimulus + " planned by LLMBrain"

    def summarize(self, stimulus):
        return stimulus + " summarized by LLMBrain"
