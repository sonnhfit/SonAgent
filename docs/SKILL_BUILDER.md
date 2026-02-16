# Dynamic Skill Generation with SkillBuilder

## Overview

The SkillBuilder skill allows SonAgent to dynamically generate, test, and save new skills at runtime. This enables the agent to learn new capabilities through natural language interaction.

## Features

- **Generate Skills from Natural Language**: Create skills from simple prompts
- **Advanced Skill Generation**: Generate skills with specific parameters and implementations
- **Sandbox Testing**: Test generated code in a safe sandbox environment before deployment
- **Runtime Loading**: Dynamically load new skills without restarting the agent
- **Secure Execution**: Restricted execution environment prevents dangerous operations

## Architecture

### Components

1. **SandboxExecutor** (`sonagent/tools/sandbox_executor.py`)
   - Executes Python code in a restricted sandbox environment
   - Captures stdout/stderr for validation
   - Enforces security restrictions on imports and builtins
   - Validates code syntax before execution

2. **SkillGenerator** (`sonagent/tools/skill_generator.py`)
   - Generates skill code from specifications
   - Uses templates to ensure consistent skill structure
   - Validates class and method names
   - Handles parameter definitions and documentation

3. **SkillBuilder** (`user_data/skills/SkillBuilder.py`)
   - User-facing skill for dynamic skill creation
   - Integrates sandbox testing with code generation
   - Saves validated skills to the skills directory
   - Provides three main methods:
     - `create_simple_skill(skill_name, prompt)`: Create from natural language
     - `generate_skill(skill_name, description, ...)`: Create with full specifications
     - `test_skill_code(code)`: Test code in sandbox

## Usage

### Example 1: Simple Skill from Prompt

```python
from SkillBuilder import SkillBuilder

builder = SkillBuilder()

# Create a simple weather checker skill
result = builder.create_simple_skill(
    skill_name='HanoiWeatherChecker',
    prompt='Check the current weather in Hanoi, Vietnam'
)
```

This generates a skill template at `user_data/skills/HanoiWeatherChecker.py` that you can then edit to add the actual implementation.

### Example 2: Advanced Skill with Parameters

```python
import json
from SkillBuilder import SkillBuilder

builder = SkillBuilder()

# Define parameters
parameters = json.dumps([
    {
        'name': 'city',
        'type': 'str',
        'description': 'Name of the city'
    },
    {
        'name': 'units',
        'type': 'str',
        'description': 'Temperature units (celsius or fahrenheit)'
    }
])

# Define implementation
implementation = '''import requests
api_key = "your-api-key"
url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units={units}&appid={api_key}"
response = requests.get(url)
data = response.json()
result = f"Temperature in {city}: {data['main']['temp']}°"
IOMsg.send_msg(result)
return result'''

# Generate the skill
result = builder.generate_skill(
    skill_name='WeatherAPI',
    description='Get weather information for a city',
    parameters=parameters,
    implementation=implementation
)
```

### Example 3: Test Code in Sandbox

```python
from SkillBuilder import SkillBuilder

builder = SkillBuilder()

test_code = '''
from pydantic import BaseModel

class TestSkill(BaseModel):
    def test_method(self, value: int):
        return value * 2
'''

result = builder.test_skill_code(test_code)
print(result)  # Will show if code is valid
```

## Chat Interface Usage

When using SonAgent through the chat interface:

```
User: Create a skill to check weather in Hanoi
Agent: [Uses SkillBuilder to generate the skill]
       ✓ Skill 'HanoiWeatherChecker' created successfully!
       
User: Reload skills
Agent: [Reloads all skills including the new one]
       Skills loaded: TextPrinter, HanoiWeatherChecker, SkillBuilder
       
User: What's the weather in Hanoi?
Agent: [Searches for relevant skills and finds HanoiWeatherChecker]
       [Executes the skill to check weather]
```

## Workflow

1. **User Request**: User asks to create a new skill through chat
2. **Skill Generation**: Agent uses SkillBuilder to generate skill code
3. **Sandbox Testing**: Code is validated in a safe sandbox environment
4. **Skill Saving**: Validated code is saved to `user_data/skills/`
5. **Skill Reloading**: Skills are reloaded to include the new skill
6. **Skill Indexing**: New skill is indexed for semantic search
7. **Skill Usage**: Agent can now use the skill in future conversations

## Security Considerations

The sandbox executor implements several security measures:

- **Restricted Imports**: Only whitelisted modules can be imported
- **Safe Builtins**: Limited set of builtin functions available
- **No File System Access**: Skills run in sandbox cannot modify files
- **No Network Access**: Network operations are restricted (except in saved skills)
- **Code Validation**: Syntax validation before execution

## Skill Template Structure

Generated skills follow this structure:

```python
from pydantic import BaseModel
from sonagent.rpc import IOMsg

class SkillName(BaseModel):
    """
    SkillName.method_name
    description: What the skill does
    args:
        - param1: Description of parameter 1
        - param2: Description of parameter 2
    """

    def method_name(self, param1: type, param2: type):
        """
        Detailed description
        
        Args:
            param1 (type): Parameter description
            param2 (type): Parameter description
        
        Returns:
            Result description
        """
        # Implementation here
        result = "Result"
        IOMsg.send_msg(result)
        return result
```

## Integration with AgentBrain

The AgentBrain automatically:
- Scans the skills directory for new skills
- Loads skill classes at startup
- Indexes skills for semantic search
- Provides skill reloading capability
- Matches user queries to relevant skills

## Limitations

1. **Template-Based Generation**: Current implementation generates basic templates
2. **Manual Implementation Required**: Complex logic requires manual coding
3. **No LLM Integration Yet**: Future versions will use LLM to generate implementations
4. **Sandbox Restrictions**: Some Python features are restricted in sandbox

## Future Enhancements

1. **LLM-Powered Generation**: Use LLM to generate complete implementations
2. **Skill Testing Framework**: Automated testing for generated skills
3. **Skill Versioning**: Track skill versions and updates
4. **Skill Dependencies**: Manage skill dependencies and prerequisites
5. **Skill Composition**: Combine multiple skills into complex workflows

## Example Files

- `examples/skill_builder_example.py`: Comprehensive examples of skill generation
- `user_data/skills/SkillBuilder.py`: The SkillBuilder skill implementation
- `sonagent/tools/sandbox_executor.py`: Sandbox execution engine
- `sonagent/tools/skill_generator.py`: Skill code generator

## Testing

Run the example to test all features:

```bash
python examples/skill_builder_example.py
```

This will:
1. Create a simple weather skill from a prompt
2. Create an advanced weather API skill with parameters
3. Test skill code in sandbox
4. Demonstrate skill reloading

## Troubleshooting

### Skill Not Loading

If a generated skill doesn't load:
1. Check the syntax of the generated code
2. Verify the skill file is in `user_data/skills/`
3. Call `reload_skills()` to reload all skills
4. Check logs for import errors

### Sandbox Errors

If sandbox execution fails:
1. Check if required imports are whitelisted
2. Verify code syntax is correct
3. Ensure no restricted operations are used
4. Review error message for specific issue

### Import Errors

If skills can't import required modules:
1. Add modules to sandbox's allowed_imports list
2. Install required packages in environment
3. Check module is available in Python path

## Contributing

To add new features to SkillBuilder:

1. Update `SandboxExecutor` for new security features
2. Enhance `SkillGenerator` templates
3. Add new methods to `SkillBuilder` skill
4. Update documentation and examples

## License

This feature is part of SonAgent and follows the same license.
