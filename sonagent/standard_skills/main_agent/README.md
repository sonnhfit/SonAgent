# Main Agent Skills

This directory contains skills specific to the main agent.

## Skill Types

### Python Skills (.py)
Python skills are executable code that the agent can use. They should follow the BaseModel pattern:

```python
from pydantic import BaseModel

class MySkill(BaseModel):
    """
    Description of what this skill does.
    """
    
    def my_method(self, param1: str) -> str:
        """Method description."""
        return f"Result: {param1}"
```

### LLM Skills (.md)
LLM skills are markdown files that provide instructions to the language model:

```markdown
# Skill Name

## Purpose
What this skill helps the agent do

## Instructions
Step-by-step instructions for the agent to follow

## Examples
Examples of how to use this skill
```

## Loading

Skills in this directory are automatically loaded for the main_agent only.
