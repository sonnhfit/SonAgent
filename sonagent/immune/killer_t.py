import os

import yaml

from sonagent.immune.immune import ImmuneCell


class KillerT(ImmuneCell):
    def __init__(self):
        super().__init__()
        self.name = "Killer T cell"
        self.target = None
        self.skills_path = os.path.join(os.path.dirname(__file__), "skills.yaml")

    def attack(self, target):
        self.target = target
        print(f"{self.name} is attacking {self.target.name}")
        self.kill()

    def kill(self):
        
        with open(self.self.skills_path, 'r') as file:
            skills_list = yaml.safe_load(file)

        # remove skill target from skills list
        skills_list.remove(self.target)

        # save again the skills list
        with open(self.skills_path, 'w') as file:
            yaml.dump(skills_list, file)
    
        if self.target is not None:
            print(f"{self.name} killed {self.target}")
            self.target = None
        else:
            print(f"{self.name} has no target to kill")
