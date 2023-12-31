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

- **Many tools and skills:** Train neural network, Search, write file, ...

### Getting Started

1. Install Dependencies

```
pip install sonagent
```

2. Run the Agent:
```
python main.py
```
output
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

### Architecture
#### Basic Idea
![Architecture](docs/source/_static/img/agent_design.png)

#### Detail design 
![Detail design](docs/source/_static/img/son_agent_design.png)


### Contributing
Contributions to enhance the Digital Consciousness Backup Agent are welcome! If you have ideas for improvements, bug fixes, or new features, feel free to open an issue or submit a pull request.


### Dev

```
pip install --editable .
```