from sonagent.nerve_system.brain_lobe import BrainLobe
from sonagent.nerve_system.language_area.gpt import GPTLlmBrain


class Brain:
    def __init__(self, brain_config={}, llm_config={}, **kwargs):

        self.language_brain: BrainLobe = None
        if llm_config.get("api_type", None) == "openai":
            self.language_brain = GPTLlmBrain()

        self.visual_brain = None
        self.auditory_brain = None
        self.movement_brain = None
