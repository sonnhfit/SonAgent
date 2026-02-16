# PythonSandboxSkill Documentation

## Overview

The `PythonSandboxSkill` is a base skill for SonAgent that allows the agent to write, validate, and execute Python code in a sandboxed environment. This skill is particularly useful for creating new skills dynamically and testing Python code safely.

## Features

1. **Safe Code Execution**: Executes Python code in an isolated subprocess with timeout limits
2. **Code Validation**: Validates Python code syntax without execution
3. **Skill Generation**: Creates new skill files for SonAgent programmatically
4. **Error Handling**: Comprehensive error handling with detailed feedback

## Available Methods

### 1. execute_python_code

Execute Python code in a sandboxed environment with timeout and resource limits.

**Syntax:**
```
PythonSandboxSkill.execute_python_code
```

**Arguments:**
- `code` (str): Python code to execute
- `timeout` (int, optional): Maximum execution time in seconds (default: 10)

**Returns:**
- String containing the output or error message

**Example Usage:**
```python
sandbox = PythonSandboxSkill()

code = """
print("Hello from sandbox!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""

output = sandbox.execute_python_code(code)
# Output: Hello from sandbox!\n2 + 2 = 4
```

**Safety Features:**
- Executes code in a separate subprocess
- Enforces timeout limits to prevent infinite loops
- Runs in a temporary directory for isolation
- Captures both stdout and stderr

### 2. validate_skill_code

Validate Python code syntax without executing it.

**Syntax:**
```
PythonSandboxSkill.validate_skill_code
```

**Arguments:**
- `code` (str): Python code to validate

**Returns:**
- String with validation result ("Code syntax is valid." or error message)

**Example Usage:**
```python
sandbox = PythonSandboxSkill()

# Valid code
result = sandbox.validate_skill_code("print('Hello')")
# Returns: "Code syntax is valid."

# Invalid code
result = sandbox.validate_skill_code("print('unclosed")
# Returns: "Syntax error: '(' was never closed at line 1"
```

### 3. write_skill

Create a new skill file for SonAgent with the provided Python code.

**Syntax:**
```
PythonSandboxSkill.write_skill
```

**Arguments:**
- `skill_name` (str): Name of the skill class (e.g., 'MyNewSkill')
- `skill_code` (str): Complete Python code for the skill including class definition
- `description` (str, optional): Description of what the skill does

**Returns:**
- Success or error message

**Example Usage:**
```python
sandbox = PythonSandboxSkill()

new_skill_code = """
from pydantic import BaseModel
from sonagent.rpc import IOMsg


class CalculatorSkill(BaseModel):
    '''
    CalculatorSkill.multiply
    description: Multiply two numbers
    args:
        - a: First number
        - b: Second number
    '''
    
    def multiply(self, a: float, b: float) -> str:
        result = a * b
        msg = f"Result: {a} * {b} = {result}"
        IOMsg.send_msg(msg)
        return msg
"""

result = sandbox.write_skill(
    "CalculatorSkill", 
    new_skill_code, 
    "A skill for calculator operations"
)
# Returns: "Successfully created skill 'CalculatorSkill' at /path/to/skills/CalculatorSkill.py"
```

## Skill Template

When creating new skills using `write_skill`, follow this template:

```python
from pydantic import BaseModel
from sonagent.rpc import IOMsg


class YourSkillName(BaseModel):
    """
    YourSkillName.method_name
    description: Description of what this method does
    args:
        - arg1: Description of first argument
        - arg2: Description of second argument
    
    YourSkillName.another_method
    description: Description of another method
    args:
        - param: Description of parameter
    """
    
    def method_name(self, arg1: type, arg2: type) -> str:
        """
        Method implementation
        """
        # Your logic here
        result = f"Processing {arg1} and {arg2}"
        IOMsg.send_msg(result)
        return result
    
    def another_method(self, param: type) -> str:
        """
        Another method implementation
        """
        # Your logic here
        result = f"Result: {param}"
        IOMsg.send_msg(result)
        return result
```

## Security Considerations

1. **Subprocess Isolation**: Code runs in a separate process, limiting impact on the main agent
2. **Timeout Protection**: Prevents infinite loops with configurable timeout
3. **Temporary Directory**: Code executes in a temp directory, not the agent's directory
4. **Syntax Validation**: Code is validated before file creation
5. **No Persistent Changes**: Executed code in sandbox doesn't affect the agent's state

## Limitations

1. **Resource Limits**: No CPU or memory limits enforced (relies on system defaults)
2. **Network Access**: Code has network access (subprocess inherits parent's network)
3. **File System**: Can access file system within subprocess permissions
4. **Import Restrictions**: Can import any installed Python packages

## Best Practices

1. **Always Validate First**: Use `validate_skill_code` before `execute_python_code`
2. **Set Appropriate Timeouts**: Adjust timeout based on expected execution time
3. **Test New Skills**: Test generated skills in isolation before using in production
4. **Document Skills**: Always provide clear descriptions when creating new skills
5. **Follow Naming Conventions**: Use descriptive class names that end with 'Skill'

## Reload Skills After Creation

After creating a new skill file, you need to reload the agent's skills:

```python
# In agent context
agent.reload_skills()
```

Or restart the agent to load new skills.

## Troubleshooting

### Issue: Timeout errors
**Solution**: Increase the timeout parameter in `execute_python_code`

### Issue: Import errors in executed code
**Solution**: Ensure required packages are installed in the environment

### Issue: Created skill not loading
**Solution**: 
1. Check that the skill file is in the correct directory (user_data/skills/)
2. Verify the class name matches the filename
3. Reload skills using `agent.reload_skills()`
4. Check for syntax errors in the skill code

### Issue: File already exists error
**Solution**: Choose a different skill name or delete the existing file first

## Example: Creating a Full Skill

Here's a complete example of using PythonSandboxSkill to create a new text manipulation skill:

```python
from user_data.skills.PythonSandboxSkill import PythonSandboxSkill

sandbox = PythonSandboxSkill()

# Define the new skill
text_skill_code = """
from pydantic import BaseModel
from sonagent.rpc import IOMsg


class TextManipulationSkill(BaseModel):
    '''
    TextManipulationSkill.uppercase
    description: Convert text to uppercase
    args:
        - text: Text to convert
    
    TextManipulationSkill.reverse
    description: Reverse the text
    args:
        - text: Text to reverse
    
    TextManipulationSkill.count_words
    description: Count words in text
    args:
        - text: Text to analyze
    '''
    
    def uppercase(self, text: str) -> str:
        result = text.upper()
        msg = f"Uppercase: {result}"
        IOMsg.send_msg(msg)
        return msg
    
    def reverse(self, text: str) -> str:
        result = text[::-1]
        msg = f"Reversed: {result}"
        IOMsg.send_msg(msg)
        return msg
    
    def count_words(self, text: str) -> str:
        word_count = len(text.split())
        msg = f"Word count: {word_count}"
        IOMsg.send_msg(msg)
        return msg
"""

# Create the skill
result = sandbox.write_skill(
    "TextManipulationSkill",
    text_skill_code,
    "A skill for text manipulation operations"
)

print(result)
# Output: Successfully created skill 'TextManipulationSkill' at /path/to/skills/TextManipulationSkill.py
```

## Integration with SonAgent

The PythonSandboxSkill integrates seamlessly with SonAgent's skill system:

1. The skill is automatically loaded when placed in `user_data/skills/`
2. Methods are indexed in the agent's memory for semantic search
3. The agent can use the skill to create new skills dynamically
4. All skills follow the same pattern for consistency

## Future Enhancements

Potential improvements for future versions:

1. Add resource limits (CPU, memory) for safer execution
2. Implement network isolation options
3. Add code linting and style checking
4. Support for async code execution
5. Skill versioning and rollback capabilities
6. Skill dependency management
