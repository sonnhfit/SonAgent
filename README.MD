## SonAgent 

### Autonomous Agent for Digital Consciousness Backup Using Large Language Models (LLM) 

[![](https://dcbadge.vercel.app/api/server/XZ8reU9z3T)](https://discord.gg/XZ8reU9z3T) 


### Overview
The Digital Consciousness Backup Agent is an autonomous system designed to safeguard your digital consciousness on the internet using Large Language Models (LLMs). As we navigate the vast landscape of the digital realm, preserving and securing our digital consciousness becomes paramount. This project employs advanced techniques to ensure the protection and backup of your digital self. Powerful code generation capability, self-editing source code
> What shapes individuals is their own beliefs. by Son Nguyen Huu

### Features
- **Autonomous Operation:** The agent operates autonomously, continuously monitoring and safeguarding your digital presence without requiring constant user intervention.

- **Belief-Based Thinking with Large Language Models (LLMs):** The agent engages in cognitive processes inspired by belief systems, utilizing advanced LLMs for reasoning and decision-making. This allows it to navigate the digital landscape with a level of understanding akin to human cognition.

- **Automatic Belief Acquisition:** The agent is designed to automatically acquire new beliefs and knowledge over time. It leverages the power of large language models to adapt and stay informed about the ever-evolving digital environment.

- **Learning with Human Feedback:** The agent incorporates human feedback into its learning process, enhancing its capabilities through continuous interaction with users. This dynamic learning mechanism ensures that the agent evolves and improves its performance based on real-world user experiences.

- **Secure Backup:** The agent employs robust encryption and secure protocols to create backups of your digital consciousness, preventing unauthorized access and ensuring the integrity of your data.
- **Self-Repairing source code**  edits its own source code and compiles itself under human approval

- **Many tools and skills:** Train neural network, Search, write file, ...
### Into and demo video 
[![SonAgent Demo](https://img.youtube.com/vi/l_aQ2RG9Np0/0.jpg)](https://www.youtube.com/watch?v=l_aQ2RG9Np0)

### Getting Started

#### 1. Install Dependencies

```
pip install sonagent
```

#### 2. Run agent

- 2.1 create `user_data` folder that will save agent skill, and user database
```
sonagent init
```
- 2.2 Please fill in the API key of openai, telegram, and github if you want the agent to create a pull request in the `user_data/config.json` file
- 2.3 run agent with file path param from step 2.1
```
sonagent run 
--config /path/to/user_data/config.json 
--agentdb sqlite:///user_data/myagentdb.sqlite 
--memory-url /path/to/user_data/memory 
--datadir /path/to/user_data/  
--user-data-dir /path/to/user_data/
```

#### 3. check rpc channal  

```
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
soon
```
## Contributors
A big thank you to all the contributors who helped improve this project. 
- Thank you from the freqtrade community, i learned a lot during my time contributing to it
- @kkmeansnt has made major contributions to documentation as well as testing
- Another colleague had interesting discussions and suggestions about autogen. thank @trungtv
- And other contributors in the [contribute tab](https://github.com/sonnhfit/SonAgent/graphs/contributors) 
- And you who have been paying attention, users and error reporting.


