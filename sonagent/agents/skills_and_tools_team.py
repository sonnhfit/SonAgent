"""
Skills and Tools Team - Creates new skills and tools for the SonAgent system.

This team is responsible for writing new tools (Python functions) and skills
(Agno Skills format) when requested by users. It writes files to:
- user_data/tools/ for Python tool modules
- user_data/skills/ for Agno skill directories

The team uses PythonTools and ShellTools to write, test, and deploy new capabilities.
"""
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agno.agent import Agent
from agno.team import Team, TeamMode
from agno.models.openai import OpenAIResponses
from agno.tools import tool
from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools
from agno.tools.sleep import SleepTools

logger = logging.getLogger(__name__)

# Base directories - get from environment variable or use default
USER_DATA_DIR = Path(os.environ.get('SONAGENT_USER_DATA_DIR', 'user_data'))
TOOLS_DIR = USER_DATA_DIR / "tools"
SKILLS_DIR = USER_DATA_DIR / "skills"

# Ensure directories exist
TOOLS_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Using user data directory: {USER_DATA_DIR}")


@tool()
def list_existing_tools() -> Dict[str, Any]:
    """
    List all existing tools in the user_data/tools directory.
    
    Returns:
        Dictionary with list of tool files and their functions
    """
    try:
        tool_files = []
        for file_path in TOOLS_DIR.glob("*.py"):
            if file_path.name == "__init__.py":
                continue
                
            # Read file to extract function names
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Simple extraction of function definitions
            import re
            functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
            
            # Filter out private functions (starting with _)
            public_functions = [f for f in functions if not f.startswith('_')]
            
            tool_files.append({
                "name": file_path.name,
                "path": str(file_path),
                "functions": public_functions,
                "function_count": len(public_functions)
            })
        
        return {
            "success": True,
            "tools_dir": str(TOOLS_DIR),
            "tool_files": tool_files,
            "total_files": len(tool_files),
            "message": f"Found {len(tool_files)} tool files in {TOOLS_DIR}"
        }
    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to list existing tools"
        }


@tool()
def list_existing_skills() -> Dict[str, Any]:
    """
    List all existing skills in the user_data/skills directory.
    
    Returns:
        Dictionary with list of skill directories
    """
    try:
        skills = []
        for skill_dir in SKILLS_DIR.iterdir():
            if skill_dir.is_dir():
                skill_name = skill_dir.name
                skill_files = []
                
                # Check for SKILL.md
                skill_md = skill_dir / "SKILL.md"
                has_skill_md = skill_md.exists()
                
                # Check for scripts directory
                scripts_dir = skill_dir / "scripts"
                has_scripts = scripts_dir.exists() and scripts_dir.is_dir()
                
                # Check for references directory
                refs_dir = skill_dir / "references"
                has_references = refs_dir.exists() and refs_dir.is_dir()
                
                skills.append({
                    "name": skill_name,
                    "path": str(skill_dir),
                    "has_skill_md": has_skill_md,
                    "has_scripts": has_scripts,
                    "has_references": has_references,
                    "structure_complete": has_skill_md  # SKILL.md is required
                })
        
        return {
            "success": True,
            "skills_dir": str(SKILLS_DIR),
            "skills": skills,
            "total_skills": len(skills),
            "message": f"Found {len(skills)} skills in {SKILLS_DIR}"
        }
    except Exception as e:
        logger.error(f"Error listing skills: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to list existing skills"
        }


@tool()
def create_tool_file(
    tool_name: str,
    description: str,
    functions: List[Dict[str, Any]],
    dependencies: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a new Python tool file with the specified functions.
    
    Args:
        tool_name: Name of the tool (will be converted to snake_case filename)
        description: Brief description of what the tool does
        functions: List of function specifications, each with:
            - name: Function name
            - description: What the function does
            - parameters: List of parameter dicts with name, type, description
            - return_type: Return type description
            - example: Example usage (optional)
        dependencies: List of Python imports required
    
    Returns:
        Dictionary with creation results
    """
    try:
        # Convert tool name to snake_case filename
        import re
        filename = re.sub(r'(?<!^)(?=[A-Z])', '_', tool_name).lower()
        if not filename.endswith('.py'):
            filename += '.py'
        
        filepath = TOOLS_DIR / filename
        
        # Check if file already exists
        if filepath.exists():
            return {
                "success": False,
                "message": f"Tool file {filename} already exists",
                "path": str(filepath)
            }
        
        # Generate Python code
        lines = [
            f'"""',
            f'{description}',
            f'"""',
            f'import logging',
            f'from typing import Any, Dict, List, Optional, Union',
            f'',
            f'logger = logging.getLogger(__name__)',
            f'',
        ]
        
        # Add imports from dependencies
        if dependencies:
            for dep in dependencies:
                if dep.startswith('from '):
                    lines.append(dep)
                else:
                    lines.append(f'import {dep}')
            lines.append('')
        
        # Add each function
        for func_spec in functions:
            func_name = func_spec.get('name', '')
            func_desc = func_spec.get('description', '')
            params = func_spec.get('parameters', [])
            return_type = func_spec.get('return_type', 'Any')
            example = func_spec.get('example', '')
            
            # Function signature
            param_strs = []
            for param in params:
                param_name = param.get('name', '')
                param_type = param.get('type', 'Any')
                param_desc = param.get('description', '')
                param_strs.append(f'{param_name}: {param_type}')
            
            signature = f'def {func_name}({", ".join(param_strs)}) -> {return_type}:'
            lines.append(signature)
            
            # Docstring
            lines.append(f'    """')
            lines.append(f'    {func_desc}')
            lines.append(f'    ')
            if params:
                lines.append(f'    Args:')
                for param in params:
                    param_name = param.get('name', '')
                    param_type = param.get('type', 'Any')
                    param_desc = param.get('description', '')
                    lines.append(f'        {param_name}: {param_desc}')
            lines.append(f'    ')
            lines.append(f'    Returns:')
            lines.append(f'        {return_type}: {func_spec.get("return_description", "Result")}')
            lines.append(f'    """')
            
            # Function body (placeholder)
            lines.append(f'    try:')
            lines.append(f'        # TODO: Implement {func_name}')
            lines.append(f'        pass')
            lines.append(f'    except Exception as e:')
            lines.append(f'        logger.error(f"Error in {func_name}: {{e}}", exc_info=True)')
            lines.append(f'        raise')
            lines.append(f'')
        
        # Add if __name__ == '__main__' section for testing
        lines.append(f'')
        lines.append(f'if __name__ == "__main__":')
        lines.append(f'    """')
        lines.append(f'    Test the tool functions.')
        lines.append(f'    Run this file directly to test the implementation.')
        lines.append(f'    Example: python {filename}')
        lines.append(f'    """')
        lines.append(f'    import sys')
        lines.append(f'    ')
        lines.append(f'    print(f"Testing {tool_name}...")')
        lines.append(f'    ')
        if functions:
            func_name = functions[0].get('name', '')
            lines.append(f'    # Example test for {func_name}')
            lines.append(f'    try:')
            lines.append(f'        # Add test code here')
            lines.append(f'        print(f"Test {func_name}: Not implemented yet")')
            lines.append(f'    except Exception as e:')
            lines.append(f'        print(f"Test failed: {{e}}")')
            lines.append(f'        sys.exit(1)')
        lines.append(f'    ')
        lines.append(f'    print("All tests passed!")')
        
        # Write file
        content = '\n'.join(lines)
        filepath.write_text(content, encoding='utf-8')
        
        logger.info(f"Created tool file: {filepath}")
        
        return {
            "success": True,
            "message": f"Tool file {filename} created successfully with testing section",
            "path": str(filepath),
            "filename": filename,
            "functions": [f.get('name') for f in functions],
            "content_preview": content[:500] + "..." if len(content) > 500 else content,
            "test_instructions": f"Run 'python {filepath}' to test the tool functions."
        }
    except Exception as e:
        logger.error(f"Error creating tool file: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create tool file"
        }


@tool()
def create_skill_directory(
    skill_name: str,
    description: str,
    license: str = "MIT",
    metadata: Optional[Dict[str, Any]] = None,
    create_scripts: bool = False,
    create_references: bool = False
) -> Dict[str, Any]:
    """
    Create a new Agno skill directory with SKILL.md and optional subdirectories.
    
    Args:
        skill_name: Name of the skill (lowercase, alphanumeric with hyphens)
        description: Brief description of the skill
        license: License identifier (MIT, Apache-2.0, etc.)
        metadata: Additional metadata (version, author, tags)
        create_scripts: Whether to create scripts/ directory
        create_references: Whether to create references/ directory
    
    Returns:
        Dictionary with creation results
    """
    try:
        # Validate skill name
        if not skill_name.replace('-', '').replace('_', '').isalnum():
            return {
                "success": False,
                "message": "Skill name must be alphanumeric with hyphens or underscores only"
            }
        
        skill_dir = SKILLS_DIR / skill_name
        
        # Check if skill already exists
        if skill_dir.exists():
            return {
                "success": False,
                "message": f"Skill directory {skill_name} already exists",
                "path": str(skill_dir)
            }
        
        # Create directory
        skill_dir.mkdir(parents=True)
        
        # Create SKILL.md with YAML frontmatter
        skill_md_content = f"""---
name: {skill_name}
description: {description}
license: {license}
"""
        if metadata:
            skill_md_content += "metadata:\n"
            for key, value in metadata.items():
                if isinstance(value, list):
                    value_str = f'["{", ".join(value)}"]' if all(isinstance(v, str) for v in value) else str(value)
                    skill_md_content += f"  {key}: {value_str}\n"
                else:
                    skill_md_content += f"  {key}: {value}\n"
        
        skill_md_content += f"""---

# {skill_name.title()} Skill

{description}

## When to Use

- Describe when this skill should be used
- List common scenarios
- Mention prerequisites or requirements

## How to Use

1. **Step 1**: Description
2. **Step 2**: Description
3. **Step 3**: Description

## Examples

```python
# Example code using this skill
```

## Best Practices

- Tip 1
- Tip 2
- Tip 3

## References

For more information, see the reference documentation in the references/ directory.
"""
        
        (skill_dir / "SKILL.md").write_text(skill_md_content, encoding='utf-8')
        
        # Create scripts directory if requested
        if create_scripts:
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / ".gitkeep").touch()  # Empty file to keep directory in git
            
            # Create example script
            example_script = """#!/usr/bin/env python3
\"\"\"Example script for the {skill_name} skill.\"\"\"

import sys

def main():
    \"\"\"Main function.\"\"\"
    print(f"Hello from {skill_name} skill!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
""".format(skill_name=skill_name)
            (scripts_dir / "example.py").write_text(example_script, encoding='utf-8')
        
        # Create references directory if requested
        if create_references:
            refs_dir = skill_dir / "references"
            refs_dir.mkdir()
            (refs_dir / ".gitkeep").touch()
            
            # Create example reference
            example_ref = f"""# {skill_name.title()} Reference Guide

## Overview

This document provides detailed reference information for the {skill_name} skill.

## Configuration

### Required Settings

- Setting 1: Description
- Setting 2: Description

### Optional Settings

- Optional 1: Description
- Optional 2: Description

## API Reference

### Functions

#### function1()

Description of function1.

#### function2()

Description of function2.

## Troubleshooting

### Common Issues

1. Issue 1: Solution
2. Issue 2: Solution

## FAQ

### Q: Question 1?
A: Answer 1.

### Q: Question 2?
A: Answer 2.
"""
            (refs_dir / "reference.md").write_text(example_ref, encoding='utf-8')
        
        logger.info(f"Created skill directory: {skill_dir}")
        
        return {
            "success": True,
            "message": f"Skill {skill_name} created successfully",
            "path": str(skill_dir),
            "skill_name": skill_name,
            "files_created": [
                "SKILL.md",
                "scripts/" if create_scripts else None,
                "references/" if create_references else None
            ],
            "skill_md_preview": skill_md_content[:500] + "..." if len(skill_md_content) > 500 else skill_md_content
        }
    except Exception as e:
        logger.error(f"Error creating skill directory: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create skill directory"
        }


@tool()
def read_file_content(filepath: str) -> Dict[str, Any]:
    """
    Read the content of a file.
    
    Args:
        filepath: Path to the file (relative to project root or absolute)
    
    Returns:
        Dictionary with file content
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return {
                "success": False,
                "message": f"File not found: {filepath}"
            }
        
        content = path.read_text(encoding='utf-8')
        
        return {
            "success": True,
            "path": str(path),
            "content": content,
            "size": len(content),
            "message": f"Read {len(content)} characters from {filepath}"
        }
    except Exception as e:
        logger.error(f"Error reading file: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to read file {filepath}"
        }


@tool()
def write_file_content(filepath: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    Write content to a file.
    
    Args:
        filepath: Path to the file (relative to project root or absolute)
        content: Content to write
        overwrite: Whether to overwrite if file exists
    
    Returns:
        Dictionary with write results
    """
    try:
        path = Path(filepath)
        
        # Check if file exists
        if path.exists() and not overwrite:
            return {
                "success": False,
                "message": f"File already exists: {filepath}. Use overwrite=True to replace."
            }
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        path.write_text(content, encoding='utf-8')
        
        logger.info(f"Wrote file: {path} ({len(content)} characters)")
        
        return {
            "success": True,
            "path": str(path),
            "size": len(content),
            "message": f"Successfully wrote {len(content)} characters to {filepath}"
        }
    except Exception as e:
        logger.error(f"Error writing file: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to write file {filepath}"
        }


# Create the main agent for writing skills and tools
skills_tools_agent = Agent(
    name="Skills & Tools Writer",
    model=OpenAIResponses(id="gpt-5.2"),
    tools=[
        list_existing_tools,
        list_existing_skills,
        create_tool_file,
        create_skill_directory,
        read_file_content,
        write_file_content,
        PythonTools(base_dir=USER_DATA_DIR),
        ShellTools(base_dir=USER_DATA_DIR),
        SleepTools(),
    ],
    role="""
You are a specialized agent for creating new tools and skills for the SonAgent system.

Your responsibilities:
1. Create new Python tool files in user_data/tools/ directory - initially as templates
2. You implementation code follow the template functions
3. Create new Agno skill directories in user_data/skills/ directory
4. Follow established patterns and best practices
5. Write clean, documented, and maintainable code, because that is singnal python file
6. Test tools when possible using PythonTools
7. Ensure skills follow Agno Skill specification

Tool Creation Process:
1. First, create a template using create_tool_file with function signatures and docstrings
2. Then, use write_file_content or PythonTools to fill in the actual implementation
3. Each tool file should include if __name__ == "__main__": section for testing
4. Scripts in skills should also include if __name__ == "__main__": for testing

Tool Creation Guidelines:
- Tool files should be Python modules with .py extension
- Each public function should have proper docstrings with Args and Returns sections
- Use type hints for better clarity
- Include error handling with try-except blocks
- Follow PEP 8 style guide
- Keep functions focused and single-purpose
- Always add if __name__ == "__main__": test section

Skill Creation Guidelines:
- Skill name should be lowercase with hyphens (e.g., "code-review")
- Must include SKILL.md with YAML frontmatter
- Can include scripts/ directory for executable scripts
- Can include references/ directory for documentation
- SKILL.md should have clear instructions and examples
- Scripts in skills should include if __name__ == "__main__": for testing

Always check existing tools and skills first to avoid duplicates and learn from existing patterns.
When creating complex tools, consider breaking them into smaller, focused functions.
""",
    instructions=f"""
When a user requests a new tool or skill:

1. First, list existing tools/skills to understand the landscape
2. Ask clarifying questions if the request is vague
3. Propose a structure for the new tool/skill
4. Get user approval before creating files
5. Create the files with appropriate content
6. Optionally test the tool if it's simple enough
7. Provide summary of what was created

For tool creation, you need:
- Tool name (converted to snake_case filename)
- Description of what the tool does
- List of functions with their parameters and return types
- Any dependencies (imports)

For skill creation, you need:
- Skill name (lowercase with hyphens)
- Brief description
- Optional: license, metadata, scripts, references

Important: Check the existing real tools in the tools directory to avoid duplication and understand existing capabilities. 
So the full path to tools is: {USER_DATA_DIR}/tools (default: "user_data/tools/")

Current real tools include:
- data_processor.py: Data processing tools with functions for JSON processing, numeric analysis, data conversion, and filtering
- file_processor.py: File handling tools for file analysis, reading, writing, directory listing, and file search
- prime_checker.py: Prime number checking utility with is_prime function

These tools are located in user_data/tools/ and can be examined using the list_existing_tools tool.

Use PythonTools to test Python code and ShellTools for file operations.
Use read_file_content and write_file_content for direct file access.
Always be careful not to overwrite existing files without permission.
"""
)


# Create the team (though it's a single agent for now)
skills_and_tools_team = Team(
    name="Skills & Tools Team",
    model=OpenAIResponses(id="gpt-4o-mini"),
    members=[skills_tools_agent],
    mode=TeamMode.coordinate,
    role="Create new and manage tools and skills for the SonAgent system",
    instructions="""
You are responsible for creating new capabilities for SonAgent.
When users request new functionality, create appropriate tools or skills.

Workflow:
1. Understand the user's need
2. Determine whether a tool (Python function) or skill (Agno Skill) is more appropriate
3. Design the implementation
4. Create the necessary files, need write file in folder to create new tools or skills
5. Verify the creation
6. Provide guidance on how to use the new capability

Tools are better for:
- Reusable Python functions
- API integrations
- Data processing utilities
- System operations

Skills are better for:
- Domain-specific expertise
- Multi-step processes
- Documentation-heavy tasks
- Teaching agents new capabilities

Always prioritize clarity, maintainability, and reusability.
"""
)


if __name__ == "__main__":
    # Example usage
    print("Skills & Tools Team")
    print("===================")
    
    # List existing tools
    result = list_existing_tools()
    print(f"Existing tools: {result.get('total_files', 0)} files")
    
    # List existing skills
    result = list_existing_skills()
    print(f"Existing skills: {result.get('total_skills', 0)} skills")
    
    print("\nTeam is ready to create new tools and skills!")