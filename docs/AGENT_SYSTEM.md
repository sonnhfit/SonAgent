# Agent System Architecture

> **⚠️ Note:** This document describes legacy architecture. For current architecture based on Agno framework with MainTeamAgent, WorkerTeamAgent, and specialized teams, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Overview

SonAgent now includes a comprehensive multi-agent system with autonomous capabilities. The system supports:

1. **Multiple Agents**: Main agent and sub-agents working together
2. **Agent Registry**: Central coordination and communication
3. **Two Skill Types**: Python code skills and LLM/markdown instruction skills
4. **Per-Agent Skills**: Each agent can have its own specialized skills
5. **Continuous Tasks**: Agents can run background tasks continuously
6. **Self-Improvement**: Agents can write and compile their own skills

## Architecture Components

### 1. Agent Registry (`sonagent/agent_registry.py`)

Central registry for managing all agents:

- **Agent Registration**: Track all active agents
- **Status Management**: Monitor agent health and status
- **Inter-Agent Communication**: Message passing between agents
- **Status History**: Track agent status changes over time

```python
from sonagent.agent_registry import AgentRegistry

registry = AgentRegistry()
# Agents register themselves automatically
```

### 2. Base Agent (`sonagent/agents/base_agent.py`)

Abstract base class for all agents:

- **Common Interface**: Standardized agent operations
- **Brain Integration**: Each agent has its own reasoning engine
- **Skills Management**: Load and manage agent-specific skills
- **Status Updates**: Report status to registry

```python
from sonagent.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    async def process(self, input_data):
        # Process input
        pass
    
    async def run_continuous(self):
        # Background tasks
        pass
```

### 3. Main Agent (`sonagent/agents/main_agent.py`)

Coordinator agent that manages the system:

- **User Communication**: Handle user queries and commands
- **Task Creation**: Create and assign tasks to agents
- **Task Monitoring**: Track task progress and status
- **Agent Coordination**: Coordinate work across sub-agents

```python
from sonagent.agents import MainAgent

main_agent = MainAgent(config, skills_manager, agent_registry)
result = await main_agent.process("Create a new task")
```

### 4. Skills Manager (`sonagent/skills/skills_manager.py`)

Enhanced to support per-agent skills:

- **Python Skills**: Load and execute Python skill code
- **LLM Skills**: Load markdown instruction files
- **Per-Agent Loading**: Load skills from agent-specific directories
- **Periodic Scanning**: Automatically detect new skills
- **Dynamic Reloading**: Reload skills without restart

```python
from sonagent.skills.skills_manager import SkillsManager

# Shared skills
skills_manager = SkillsManager(sonagent)

# Agent-specific skills
agent_skills = SkillsManager(sonagent, agent_id="my_agent")
```

### 5. Continuous Worker (`sonagent/continuous_worker.py`)

Background worker for continuous tasks:

- **Task Execution**: Execute pending tasks asynchronously
- **Agent Loops**: Run agent continuous tasks
- **Periodic Maintenance**: Skill reloading, cleanup
- **Self-Improvement**: Support for autonomous improvements

```python
from sonagent.continuous_worker import start_continuous_worker

worker = start_continuous_worker(agent_registry)
# Worker runs in background
```

## Skills System

### Python Skills

Located in `user_data/skills/` (shared) or `user_data/skills/{agent_id}/` (agent-specific):

```python
from pydantic import BaseModel

class MySkill(BaseModel):
    """
    A skill that does something useful.
    """
    config: dict = {}
    
    def __init__(self, **data):
        super().__init__(**data)
    
    def my_method(self, param: str) -> str:
        """Execute the skill."""
        return f"Processed: {param}"
```

### LLM Skills (Markdown)

Instruction files that guide the agent's behavior:

```markdown
# My LLM Skill

## Purpose
Guide the agent on how to perform a specific task

## Instructions
1. Understand the user's request
2. Break down the task
3. Execute step by step
4. Report results

## Examples
- Example 1: ...
- Example 2: ...
```

### Skill Organization

Agent-specific skills are automatically copied from `sonagent/standard_skills/{agent_id}/` to `user_data/skills/{agent_id}/` at startup.

**Standard Skills Structure:**
```
sonagent/standard_skills/
├── SkillBuilder.py          # Shared skills (copied to user_data/skills/)
├── TextPrinter.py
├── main_agent/              # Main agent starter skills
│   ├── TaskManagement.md   # LLM skill
│   └── README.md
└── {agent_id}/              # Agent-specific starter skills
```

**User Skills Directory (Runtime):**
```
user_data/skills/
├── .gitkeep                 # Shared skills (all agents)
├── SkillBuilder.py          # Copied from standard_skills/
├── TextPrinter.py
├── main_agent/              # Main agent skills (copied at startup)
│   ├── TaskManagement.md   # LLM skill
│   └── README.md
└── data_agent/              # Data agent skills (copied at startup)
    ├── DataAnalysis.py     # Python skill
    └── DataProcessing.md   # LLM skill
```

**Note:** Skills in `user_data/skills/` are automatically created at startup from the standard skills template. You can add custom skills directly to `user_data/skills/{agent_id}/` or place them in `sonagent/standard_skills/{agent_id}/` to have them copied automatically.

## Usage Examples

### Creating an Agent System

```python
from sonagent.agent_registry import AgentRegistry
from sonagent.agents import MainAgent
from sonagent.skills.skills_manager import SkillsManager
from sonagent.continuous_worker import start_continuous_worker

# Initialize registry
registry = AgentRegistry()

# Create main agent
main_agent = MainAgent(config, skills_manager, registry)

# Start continuous worker
worker = start_continuous_worker(registry)

# Process user input
result = await main_agent.process("List all tasks")
```

### Creating a Sub-Agent

```python
from sonagent.agents.base_agent import BaseAgent
from sonagent.skills.skills_manager import SkillsManager

class DataAgent(BaseAgent):
    async def process(self, input_data):
        # Process data-related tasks
        return await self.chat(input_data)
    
    async def run_continuous(self):
        # Continuous data monitoring
        while self.running:
            await self._monitor_data()
            await asyncio.sleep(60)

# Create with agent-specific skills
skills = SkillsManager(sonagent, agent_id="data_agent")
data_agent = DataAgent("data_agent", "Data Agent", config, skills, registry)
```

### Task Management

```python
# Create a task
result = await main_agent.process({
    'command': 'create_task',
    'content': 'Analyze the latest data',
    'priority': 5,
    'agent_id': 'data_agent'
})

# List tasks
result = await main_agent.process({'command': 'list_tasks'})

# Check task status
result = await main_agent.process({
    'command': 'get_task_status',
    'task_id': 123
})

# Kill a task
result = await main_agent.process({
    'command': 'kill_task',
    'task_id': 123
})
```

### Inter-Agent Communication

```python
# Send message from one agent to another
registry.send_message(
    from_agent_id="main_agent",
    to_agent_id="data_agent",
    message="Please process the new dataset",
    message_type="command"
)

# Broadcast to all agents
registry.broadcast_message(
    from_agent_id="main_agent",
    message="System maintenance starting in 5 minutes",
    message_type="announcement"
)

# Get messages for an agent
messages = registry.get_messages("data_agent", limit=10)
```

## Configuration

Add to your `config.json`:

```json
{
  "user_data_dir": "user_data",
  "agents": {
    "main_agent": {
      "enabled": true,
      "skills_dir": "skills/main_agent"
    },
    "data_agent": {
      "enabled": true,
      "skills_dir": "skills/data_agent"
    }
  },
  "continuous_worker": {
    "enabled": true,
    "check_interval": 5,
    "skill_scan_interval": 60
  }
}
```

## Best Practices

1. **Skill Organization**: Keep agent-specific skills in agent directories
2. **Naming Conventions**: Use clear, descriptive names for agents and skills
3. **Error Handling**: Always handle errors gracefully in agent code
4. **Status Updates**: Update agent status regularly for monitoring
5. **Resource Management**: Clean up resources in agent shutdown
6. **Logging**: Use appropriate log levels for different events
7. **Testing**: Test skills independently before integration

## Advanced Features

### Self-Improvement

Agents can write their own skills:

```python
# Use SkillBuilder skill
result = await agent.chat("Create a skill to calculate Fibonacci numbers")
# Agent will use SkillBuilder to generate, test, and save the skill
```

### Dynamic Skill Loading

Skills are automatically reloaded when files change:

```python
# Skills are scanned every 60 seconds
# New skills are loaded automatically
# Modified skills are reloaded
```

### Task Prioritization

Tasks are executed based on priority:

```python
# Higher priority tasks execute first
Task.create_task(
    agent_id="main_agent",
    content="Critical security update",
    priority=10  # High priority
)

Task.create_task(
    agent_id="main_agent",
    content="Routine maintenance",
    priority=1  # Low priority
)
```

## Troubleshooting

### Skills Not Loading

1. Check skill file syntax
2. Verify directory structure
3. Check logs for errors
4. Ensure BaseModel inheritance for Python skills

### Agent Communication Issues

1. Verify agent is registered
2. Check agent_id spelling
3. Review message logs
4. Check registry status

### Task Execution Problems

1. Verify agent is running
2. Check task status in database
3. Review continuous worker logs
4. Ensure agent has required skills

## Migration Guide

### From Old System

The legacy `Agent` class still works but now includes the new system:

```python
# Old code still works
agent = Agent(memory_path, skills, config)
result = await agent.chat("Hello")

# New features available
agent.main_agent.process({'command': 'list_agents'})
agent.agent_registry.get_all_agents()
```

### Adding Agent Support

To enable multi-agent features in existing code:

1. Import new classes
2. Initialize agent registry
3. Create main agent
4. Start continuous worker
5. Create sub-agents as needed

## API Reference

See individual module documentation for detailed API reference:

- `sonagent.agent_registry.AgentRegistry`
- `sonagent.agents.base_agent.BaseAgent`
- `sonagent.agents.main_agent.MainAgent`
- `sonagent.skills.skills_manager.SkillsManager`
- `sonagent.continuous_worker.ContinuousTaskWorker`
