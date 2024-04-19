from sonagent.nerve_system.brain_lobe import BrainLobe
from sonagent.nerve_system.language_area.llm_brain import LLMBrain


class Brain:
    def __init__(self, brain_config={}):
        self.language_brain: BrainLobe = LLMBrain()
        self.visual_brain = None
        self.auditory_brain = None
        self.movement_brain = None
