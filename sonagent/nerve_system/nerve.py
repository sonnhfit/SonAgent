from sonagent.nerve_system.brain_lobe import BrainLobe


class Nerve:
    def stimulation(self, stimulus):
        BrainLobe.shm_nerve['stimulus'] = stimulus
