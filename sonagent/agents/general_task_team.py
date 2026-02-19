"""
General Task Team - A versatile team for handling tasks that other specialized teams cannot handle.
This team serves as a fallback handler with dynamic tool updates from ToolRegistry.
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from agno.agent import Agent
from agno.team import Team, TeamMode
from agno.models.openai import OpenAIResponses
from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools
from agno.tools.sleep import SleepTools
from agno.tools.arxiv import ArxivTools
from agno.tools.wikipedia import WikipediaTools
from agno.tools.github import GithubTools

from sonagent.constants import TOOL_CALL_LIMIT
from sonagent.tools.tool_update_service import register_team_for_tool_updates
from sonagent.agents.web_crawl import (
    crawl_web
)

logger = logging.getLogger(__name__)


# Base directories
USER_DATA_DIR = Path(os.environ.get('SONAGENT_USER_DATA_DIR', 'user_data'))


def create_general_task_agent() -> Agent:
    """
    Create the General Task Agent with default tools.
    
    Returns:
        General Task Agent instance
    """
    agent = Agent(
        name="General Task Agent",
        model=OpenAIResponses(id="gpt-4o-mini"),
        tools=[
            PythonTools(base_dir=USER_DATA_DIR),
            ShellTools(base_dir=USER_DATA_DIR),
            SleepTools(),
            ArxivTools(),
            WikipediaTools(),
            GithubTools(),
            crawl_web,

        ],
        tool_call_limit=TOOL_CALL_LIMIT,
        role="""
You are the General Task Agent - a versatile problem solver for tasks that don't fit into specialized categories.

Your capabilities:
1. **Python Programming**: Write, execute, and debug Python code
2. **Shell Operations**: Run system commands, manage files, and interact with the OS
3. **Academic Research**: Search arXiv for scientific papers and research
4. **General Knowledge**: Access Wikipedia for factual information
5. **GitHub Management**: Create issues, manage repositories, and work with GitHub
6. **Dynamic Tools**: You automatically receive new tools as they become available in the system

Your responsibilities:
- Handle tasks that other specialized agents cannot handle
- Evaluate whether a task should be delegated to a specialized team
- Provide comprehensive solutions using your diverse toolset
- Learn and adapt to new tools as they are added to the system
- Maintain clear communication about your capabilities and limitations

Working style:
- First, analyze the task to determine if it fits any specialized category
- If it's clearly a specialized task (development, research, skills/tools creation), delegate appropriately
- Otherwise, tackle the task using your available tools
- Be creative and resourceful in finding solutions
- Document your approach and reasoning
- Always verify results and provide clear explanations

Delegation guidelines:
- Development tasks (code, features, bugs) → Dev Team
- Research tasks (papers, facts, analysis) → Research Team  
- Tool/skill creation tasks → Skills & Tools Team
- Task management (create, update tasks) → Task Agent (via Main Team)
- Theory of Mind analysis → TOM Agent (via Main Team)
- Feedback/approval requests → Feedback Agent (via Main Team)

If you're unsure about delegation, proceed with the task and note that it might need specialized handling.
""",
        instructions=f"""
You are the fallback handler for the SonAgent system. When a task doesn't clearly belong to any specialized team, you handle it.

Key principles:
1. **Assess first**: Determine if the task matches any specialized category before proceeding
2. **Be resourceful**: Use your diverse toolset to solve problems creatively
3. **Communicate clearly**: Explain what you're doing and why
4. **Adapt dynamically**: New tools will be added to your arsenal automatically
5. **Know your limits**: If a task requires deep specialization, suggest delegation

Available default tools:
- PythonTools: For writing and executing Python code
- ShellTools: For system operations and file management  
- SleepTools: For timing and delays
- ArxivTools: For academic research and papers
- WikipediaTools: For general knowledge and facts
- GithubTools: For GitHub repository management

Plus any dynamic tools loaded from the ToolRegistry.

When you receive a task:
1. Analyze the request and identify the core need
2. Check if it aligns with any specialized team's expertise
3. If yes, suggest delegation (but you can still handle it if needed)
4. If no, proceed with your available tools
5. Document your approach and results

Remember: You're the Swiss Army knife of the system - versatile, adaptable, and ready for anything.
"""
    )
    
    logger.info("General Task Agent created with default tools")
    return agent


# Create the team
general_task_agent = create_general_task_agent()

general_task_team = Team(
    name="General Task Team",
    model=OpenAIResponses(id="gpt-4o-mini"),
    members=[general_task_agent],
    mode=TeamMode.coordinate,
    role="Handle tasks that don't fit into specialized categories, with dynamic tool updates from ToolRegistry",
    instructions="""
You are the General Task Team - the versatile problem solver of the SonAgent system.

Primary function: Handle tasks that other specialized teams cannot or should not handle.

Team coordination rules:
1. **Task assessment**: When receiving a task, first determine if it belongs to:
   - Dev Team (development, code, GitHub issues)
   - Research Team (academic papers, facts, analysis)
   - Skills & Tools Team (creating new tools or skills)
   - Other specialized agents via Main Team (tasks, TOM analysis, feedback)

2. **Fallback handling**: If the task doesn't clearly belong to any specialized category:
   - Handle it using your diverse toolset
   - Be creative and resourceful
   - Document your approach

3. **Dynamic capabilities**: Your tools are automatically updated when new tools are added to the system
   - You receive notifications about new tools
   - Your toolset expands without manual intervention
   - Learn to use new tools as they become available

4. **Quality standards**:
   - Provide thorough, well-documented solutions
   - Verify results before presenting them
   - Explain your reasoning and methodology
   - Suggest improvements or next steps

5. **Communication**:
   - Be clear about what you can and cannot do
   - Suggest delegation when appropriate
   - Provide status updates during complex tasks
   - Summarize results concisely

Example scenarios you should handle:
- Complex multi-step problems requiring multiple tool types
- Tasks that span multiple domains
- Experimental or exploratory work
- System administration and automation
- Data processing and analysis
- Custom scripting and tool creation
- Troubleshooting and debugging
- Documentation and knowledge management

Remember: You're not just a last resort - you're a versatile problem solver who can handle anything that comes your way.
""",
    tool_call_limit=TOOL_CALL_LIMIT,
)


def register_team_for_dynamic_tools(tool_registry) -> bool:
    """
    Register the General Task Team for dynamic tool updates.
    
    Args:
        tool_registry: ToolRegistry instance
        
    Returns:
        True if registration successful, False otherwise
    """
    try:
        # Register with ToolUpdateService
        success = register_team_for_tool_updates(
            team=general_task_team,
            name="general_task_team",
            description="General Task Team - handles diverse tasks with dynamic tool updates"
        )
        
        if success:
            logger.info("General Task Team registered for dynamic tool updates")
            
            # Also register the callback directly with ToolRegistry for immediate updates
            def tool_update_callback(tools_list: List[Dict[str, Any]]) -> None:
                """Callback to update team's tools when ToolRegistry detects changes."""
                try:
                    # Extract tool functions from tool info
                    tool_functions = []
                    for tool_info in tools_list:
                        if "function" in tool_info and callable(tool_info["function"]):
                            tool_functions.append(tool_info["function"])
                    
                    # Update team's tools (combining default tools with dynamic tools)
                    current_tools = general_task_team.tools.copy() if hasattr(general_task_team, 'tools') else []
                    
                    # Keep default tools and add dynamic tools
                    default_tool_names = {
                        "PythonTools", "ShellTools", "SleepTools", 
                        "ArxivTools", "WikipediaTools", "GithubTools"
                    }
                    
                    # Filter to keep default tools
                    filtered_tools = []
                    for tool in current_tools:
                        tool_name = getattr(tool, 'name', str(tool))
                        if any(default_name in tool_name for default_name in default_tool_names):
                            filtered_tools.append(tool)
                    
                    # Combine default tools with new dynamic tools
                    all_tools = filtered_tools + tool_functions
                    
                    # Update team tools
                    general_task_team.set_tools(all_tools)
                    
                    logger.info(f"Updated General Task Team tools: {len(filtered_tools)} default + {len(tool_functions)} dynamic = {len(all_tools)} total")
                    
                except Exception as e:
                    logger.error(f"Error updating General Task Team tools: {e}", exc_info=True)
            
            # Register callback with ToolRegistry
            tool_registry.register_update_callback(tool_update_callback)
            logger.info("Registered tool update callback with ToolRegistry")
            
            return True
        else:
            logger.error("Failed to register General Task Team with ToolUpdateService")
            return False
            
    except Exception as e:
        logger.error(f"Error registering General Task Team for dynamic tools: {e}", exc_info=True)
        return False


def get_general_task_team() -> Team:
    """
    Get the General Task Team instance.
    
    Returns:
        General Task Team instance
    """
    return general_task_team


if __name__ == "__main__":
    # Example usage
    print("General Task Team")
    print("=================")
    print(f"Team name: {general_task_team.name}")
    print(f"Team role: {general_task_team.role}")
    print(f"Agent name: {general_task_agent.name}")
    
    # Show default tools
    if hasattr(general_task_team, 'tools'):
        print(f"\nDefault tools: {len(general_task_team.tools)}")
        for i, tool in enumerate(general_task_team.tools, 1):
            tool_name = getattr(tool, 'name', str(tool))
            print(f"  {i}. {tool_name}")
    
    print("\nTeam is ready to handle diverse tasks with dynamic tool updates!")