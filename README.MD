## SonAgent 

### Autonomous Agent for Digital Consciousness Backup Using Large Language Models (LLM)

### Overview
The Digital Consciousness Backup Agent is an autonomous system designed to safeguard your digital consciousness on the internet using Large Language Models (LLMs). As we navigate the vast landscape of the digital realm, preserving and securing our digital consciousness becomes paramount. This project employs advanced techniques to ensure the protection and backup of your digital self.
> What shapes individuals is their own beliefs. by Son Nguyen Huu

### Features
- **Autonomous Operation:** The agent operates autonomously, continuously monitoring and safeguarding your digital presence without requiring constant user intervention.

- **Belief-Based Thinking with Large Language Models (LLMs):** The agent engages in cognitive processes inspired by belief systems, utilizing advanced LLMs for reasoning and decision-making. This allows it to navigate the digital landscape with a level of understanding akin to human cognition.

- **Automatic Belief Acquisition:** The agent is designed to automatically acquire new beliefs and knowledge over time. It leverages the power of large language models to adapt and stay informed about the ever-evolving digital environment.

- **Learning with Human Feedback:** The agent incorporates human feedback into its learning process, enhancing its capabilities through continuous interaction with users. This dynamic learning mechanism ensures that the agent evolves and improves its performance based on real-world user experiences.

- **Secure Backup:** The agent employs robust encryption and secure protocols to create backups of your digital consciousness, preventing unauthorized access and ensuring the integrity of your data.
- **Self-Repairing source code**  edits its own source code and compiles itself under human approval

- **Many tools and skills:** Train neural network, Search, write file, ...

### Getting Started

1. Install Dependencies

```
pip install sonagent
```

2. Test the Agent:
```
python main.py
```
output

3. Run bot 

```
sonagent run
```
### Some Demo 

```
{
    "input": "Train neural network for image classification of digits 0-9",
    "subtasks": [
        {"function": "PyTorchSkill.SetupEnvironment"},
        {"function": "PyTorchSkill.CreateCNN", "args": {"architecture": "ResNet50"}},
        {"function": "PyTorchSkill.PreprocessData", "args": {"data": "MNIST"}},
        {"function": "PyTorchSkill.TrainModel", "args": {"epochs": 10}},
        {"function": "PyTorchSkill.EvaluateModel"},
        {"function": "PyTorchSkill.SaveModel"}
    ]
}
```


### Dev

```
pip install --editable .
```

if you want to build docker image 
```
docker build --pull --rm -f "Dockerfile" -t sonnhfit/sonagent:dev "." --platform=linux/amd64
```
## Contributors
A big thank you to all the contributors who helped improve this project

