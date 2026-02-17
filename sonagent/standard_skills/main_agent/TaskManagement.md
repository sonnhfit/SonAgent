# Task Management Skill

## Purpose
This skill helps the main agent manage tasks effectively, including creating, monitoring, and coordinating task execution.

## Instructions

### When to Use This Skill
- User asks about tasks or their status
- Need to create a new task
- Need to assign work to sub-agents
- Need to check on running tasks

### Creating Tasks
1. Understand the user's request clearly
2. Break down complex requests into smaller tasks if needed
3. Assign appropriate priority (0-10, higher is more urgent)
4. Consider which agent should handle the task (main_agent or specific sub-agent)

### Monitoring Tasks
1. Check task status regularly
2. Report progress to users when asked
3. Identify stuck or failed tasks
4. Take corrective action if needed

### Coordinating Work
1. Distribute tasks across available agents
2. Monitor agent workload
3. Rebalance work if one agent is overloaded
4. Ensure critical tasks are prioritized

## Examples

### Example 1: Creating a Simple Task
User: "Can you analyze the latest data?"
Response: "I'll create a task to analyze the latest data. This will be assigned to the data analysis agent with normal priority."

### Example 2: Checking Task Status
User: "What's the status of my tasks?"
Response: "Let me check your current tasks..." (then list tasks with their status)

### Example 3: Complex Task Breakdown
User: "Generate a comprehensive report with analysis and visualization"
Response: "I'll break this down into subtasks:
1. Data collection and preprocessing
2. Statistical analysis
3. Visualization creation
4. Report generation
Each will be assigned to the appropriate specialist agent."

## Best Practices
- Always acknowledge the user's request
- Provide clear status updates
- Break complex tasks into manageable pieces
- Prioritize based on urgency and importance
- Keep users informed of progress
