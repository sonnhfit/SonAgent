from sonagent.nervous_system.brain import Brain


class Nerve:
    def stimulation(self, stimulus):
        Brain.shm_nerve['stimulus'] = stimulus
