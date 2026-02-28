# SonAgent Architecture Documentation

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Core Components](#core-components)
- [Specialized Teams](#specialized-teams)
- [Task System](#task-system)
- [Tool Registry](#tool-registry)
- [Data Flow](#data-flow)

---

## Overview

SonAgent is an autonomous digital consciousness backup system built on the **Agno framework**, utilizing Large Language Models (LLMs) for belief-based reasoning and decision-making. The architecture employs a multi-agent team coordination system where specialized teams handle different domains, enabling complex problem-solving with human-in-the-loop feedback.

### Key Features
- **Multi-Agent Coordination**: Team-based architecture with specialized agents
- **Autonomous Task Execution**: Self-prioritizing task queue with token tracking
- **Dynamic Tool Loading**: Runtime tool updates from `user_data/tools/`
- **Persistent Memory**: ChromaDB vector store with chat history
- **Human Feedback Integration**: Learning machine with approval workflows
- **RPC Integration**: Telegram, WebSocket, and API interfaces

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Worker Process                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                       SonBot                           │ │
│  │  ┌──────────────────┐        ┌────────────────────┐  │ │
│  │  │  MainTeamAgent   │◄──────►│ WorkerTeamAgent    │  │ │
│  │  │  (Coordination)  │        │ (Execution)        │  │ │
│  │  └────────┬─────────┘        └─────────┬──────────┘  │ │
│  │           │                             │             │ │
│  │           ▼                             ▼             │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │         Specialized Teams                       │ │ │
│  │  │  - Dev Team        - Research Team              │ │ │
│  │  │  - Finance Team    - Skills & Tools Team        │ │ │
│  │  │  - General Task Team                            │ │ │
│  │  └─────────────────────────────────────────────────┘ │ │
│  │                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │ ToolRegistry │  │ RPC Manager  │  │  Database  │ │ │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         ▲                      ▲                    ▲
         │                      │                    │
    Telegram Bot           WebSocket API         REST API
```

---

## Core Components

### Worker

**Location**: `sonagent/worker.py`

The Worker is the main process orchestrator that manages the SonAgent lifecycle.

#### Responsibilities
- State machine management (`STOPPED` → `RUNNING` → `RELOAD_CONFIG`)
- Process throttling and rate control
- Systemd integration for service management
- Instantiates and manages SonBot

#### State Machine
```python
State.STOPPED     # Idle, waiting for activation
State.RUNNING     # Active processing
State.RELOAD_CONFIG  # Configuration reload
```

---

### SonBot

**Location**: `sonagent/sonbot.py`

SonBot is the central coordinator that initializes team agents and manages RPC communication.

#### Initialization Flow
1. Initialize database (SQLAlchemy)
2. Create MainTeamAgent (user-facing coordination)
3. Create WorkerTeamAgent (autonomous task execution)
4. Initialize SkillsManager (dynamic skill loading)
5. Initialize ToolRegistry (dynamic tool discovery)
6. Create RPC Manager (Telegram, WebSocket, API)
7. Start monitoring services

#### Key Attributes
```python
self.team_agent: MainTeamAgent      # Handles user requests
self.worker_team_agent: WorkerTeamAgent  # Autonomous task execution
self.tool_registry: ToolRegistry    # Dynamic tool loading
self.skills: SkillsManager          # Skill management
self.rpc: RPCManager               # Communication channels
self.conversation_id: str           # Global conversation context
```

---

### MainTeamAgent

**Location**: `sonagent/agents/main_team.py`

The primary coordination hub that routes user requests to specialized teams using Agno's Team abstraction.

#### Architecture
```python
MainTeamAgent (Team.coordinate)
├── Task Agent         # Task creation, scheduling, reminders
├── TOM Agent          # Theory of Mind - beliefs, desires, targets
├── Feedback Agent     # Human approval workflow
├── Assistant Agent    # General queries and interface
├── Knowledge Base     # ChromaDB vector store
└── Specialized Teams
    ├── Dev Team
    ├── Research Team
    ├── Finance Team
    ├── Skills & Tools Team
    └── General Task Team
```

#### Agents

##### 1. Task Agent
**Role**: Task Manager and Reminder Specialist

**Tools**:
- `create_task_tool` - Create new tasks
- `get_tasks_tool` - Query tasks
- `update_task_tool` - Update status/priority
- `delete_task_tool` - Remove tasks

**Capabilities**:
- Create tasks with priority levels (0-2)
- Schedule tasks with `scheduled_at` datetime
- Set recurring tasks with `cron_expression`
- Track task status: pending → in_progress → done/failed/cancelled

##### 2. TOM (Theory of Mind) Agent
**Role**: Theory of Mind Specialist

**Tools**:
- `get_targets_tool` - Query objectives
- `add_target_tool` - Create new goals
- `update_target_tool` - Update progress
- `delete_target_tool` - Remove targets

**Capabilities**:
- Analyze user beliefs, desires, and intentions
- Manage short-term and long-term objectives (Targets)
- Track goal progress (0-100%)
- Token usage tracking per target

##### 3. Feedback Agent
**Role**: Human Feedback Collector

**Tools**:
- `request_feedback_tool` - Request approval
- `process_feedback_tool` - Handle responses

**Capabilities**:
- Request human approval for critical actions
- Process approval/rejection responses
- Integration with learning machine

##### 4. Assistant Agent
**Role**: Helpful Assistant

**Capabilities**:
- General conversation
- Cross-domain query handling
- Fallback for unrouted requests

#### Knowledge Base
Uses ChromaDB vector store with OpenAI embeddings for persistent knowledge storage:
```python
Knowledge(
    name="Knowledge Base",
    vector_db=ChromaDb(
        collection="vectors",
        path="user_data/chromadb",
        embedder=OpenAIEmbedder(id="text-embedding-3-small")
    )
)
```

#### Learning Machine
Implements agentic learning with user profiles and memory:
```python
LearningMachine(
    mode=LearningMode.AGENTIC,
    user_profile=UserProfileConfig(enabled=True),
    user_memory=UserMemoryConfig(enabled=True),
    learned_knowledge=LearnedKnowledgeConfig(enabled=True)
)
```

---

### WorkerTeamAgent

**Location**: `sonagent/agents/worker_team.py`

Autonomous task executor that prioritizes and executes tasks based on value scoring.

#### Architecture
```python
WorkerTeamAgent (Team.coordinate)
├── Worker Agent       # Task prioritization and execution
├── Target Agent       # Goal management
└── Specialized Teams  # Delegates to specialized teams
```

#### Task Prioritization Algorithm

Tasks are prioritized using a value score:
```python
def get_task_value_score() -> float:
    priority_weight = priority * 10  # 0-20 points
    token_weight = -estimated_tokens / 1000  # Penalty for expensive tasks
    goal_alignment = calculate_alignment_with_targets()  # 0-30 points
    
    return priority_weight + token_weight + goal_alignment
```

#### Execution Flow
1. Worker Agent fetches pending tasks
2. Calculate value scores for all tasks
3. Select highest-value task
4. Delegate to appropriate specialized team
5. Track execution time and token usage
6. Update task metrics (execution_count, total_tokens_used, etc.)
7. Send RPC notification
8. Update target progress
9. Repeat

---

## Specialized Teams

### Dev Team
**Location**: `sonagent/agents/dev_team.py`

Handles software development tasks with GitHub integration.

**Agents**:
- **Product Owner Agent**: Requirements to GitHub issues
- **Backend Dev Agent**: Backend implementation
- **Frontend Dev Agent**: UI/UX implementation

**Use Cases**: Feature implementation, bug fixes, code refactoring, GitHub issue management

---

### Research Team
**Location**: `sonagent/agents/research_team.py`

Conducts academic and market research.

**Agents**:
- **ArXiv Researcher**: Academic papers
- **Wikipedia Researcher**: General knowledge
- **HackerNews Analyst**: Tech trends
- **YFinance Analyst**: Financial data

**Use Cases**: Academic research, market analysis, technology trend monitoring, fact-checking

---

### Finance Team
**Location**: `sonagent/agents/finance_team.py`

Specializes in financial analysis and market research.

**Agents**:
- **HackerNews Analyst**: Tech investment trends
- **Finance Analyst**: Market analysis

**Capabilities**: Stock price monitoring, company fundamentals, analyst recommendations, investment research

---

### Skills and Tools Team
**Location**: `sonagent/agents/skills_and_tools_team.py`

Extends system capabilities by creating new tools and skills dynamically.

**Capabilities**:
- Create Python tools in `user_data/tools/`
- Create Agno skills in `user_data/skills/`
- List existing tools
- Execute Python code for testing
- Run shell commands

**Tool Creation Workflow**:
1. User requests new capability
2. Skills & Tools Team designs tool
3. Creates .py file in user_data/tools/
4. ToolRegistry auto-detects new file
5. Tool becomes available to all teams
6. ToolUpdateService notifies subscribers

---

### General Task Team
**Location**: `sonagent/agents/general_task_team.py`

Handles cross-domain tasks that don't fit specialized teams.

**Features**:
- Dynamic tool integration from ToolRegistry
- Receives automatic tool updates when new tools are added
- Cross-domain problem solving

**Use Cases**: Complex multi-step problems, system automation, data processing, custom workflows

---

## Task System

### Task Model
**Location**: `sonagent/persistence/tasks_models.py`

#### Key Fields
```python
id: int                       # Primary key
agent_id: str                 # Owner agent
content: str                  # Task description
status: str                   # pending/in_progress/done/failed/cancelled
priority: int                 # 0 (low) - 2 (high)
payload: Dict[str, Any]       # Additional data
result: Dict[str, Any]        # Execution result
scheduled_at: datetime        # One-time execution
cron_expression: str          # Recurring (e.g., "0 9 * * MON")
execution_count: int          # Times executed
total_tokens_used: int        # Cumulative tokens
last_execution_tokens: int    # Last run tokens
last_execution_duration: float  # Seconds
success_rate: float           # 0.0 - 1.0
retry_count: int              # Current attempts
max_retries: int              # Max allowed (default: 3)
```

#### Key Methods
```python
@staticmethod
def create_task(agent_id, content, priority=0, payload=None, 
                scheduled_at=None, cron_expression=None) -> Task

def start() -> None
def complete(result=None) -> None
def fail(error_message=None) -> None
def retry() -> bool
def update_execution_data(tokens_used, duration_seconds, success=True) -> None
def get_task_value_score() -> float
```

#### Task Status Lifecycle
```
pending → in_progress → done
                     ↓
                   failed → retry → pending (if retries remain)
                     ↓
                 cancelled
```

### Target Model

Represents goals and objectives that guide task prioritization.

#### Key Fields
```python
id: int
target: str              # Goal description
description: str         # Detailed explanation
progress: int            # 0-100%
status: str             # active/completed
start_date: datetime
target_date: datetime   # Deadline
tokens_used: int        # Token investment
```

### Task Creation Examples

```python
# Simple task
Task.create_task(
    agent_id="user_123",
    content="Research latest AI papers on transformers",
    priority=1
)

# Scheduled task
Task.create_task(
    agent_id="user_123",
    content="Send daily summary",
    scheduled_at=datetime(2024, 1, 15, 9, 0)
)

# Recurring task
Task.create_task(
    agent_id="user_123",
    content="Weekly backup",
    cron_expression="0 2 * * SUN"  # Every Sunday at 2 AM
)

# High-priority with payload
Task.create_task(
    agent_id="user_123",
    content="Generate financial report",
    priority=2,
    payload={"company": "AAPL", "report_type": "quarterly"}
)
```

---

## Tool Registry

### ToolRegistry
**Location**: `sonagent/tools/tool_registry.py`

Dynamically loads and manages tools from `user_data/tools/` directory.

#### Features
- Auto-scans for changes every 30 seconds
- File hash-based change detection
- Supports private functions (prefixed with `_`)
- Dynamic module import
- Tool metadata generation

#### Tool Structure
```python
# user_data/tools/my_tool.py

def calculate_fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number.
    
    Args:
        n: Position in sequence (0-indexed)
        
    Returns:
        The nth Fibonacci number
    """
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def _helper_function(x):
    """Private helper (ignored by registry)"""
    return x * 2
```

### ToolUpdateService
**Location**: `sonagent/tools/tool_update_service.py`

Manages dynamic tool updates for teams and agents.

#### Features
- Background monitoring thread
- Subscriber pattern for teams/agents
- Automatic tool distribution on changes
- Manual update triggers

#### Update Flow
1. File change in user_data/tools/
2. ToolRegistry detects change
3. ToolRegistry reloads tools
4. ToolUpdateService notified
5. Subscribers receive new tools via callbacks
6. Tools immediately available

---

## Data Flow

### User Request Flow
```
1. User sends message via Telegram/API/WebSocket
2. RPC Manager receives message
3. Forwards to SonBot
4. SonBot routes to MainTeamAgent
5. MainTeamAgent analyzes and routes to specialized team
6. Team executes task
7. Results stored in database
8. Response sent back to user via RPC
9. Chat history persisted
```

### Autonomous Task Execution Flow
```
1. WorkerTeamAgent fetches pending tasks
2. Calculate value scores
3. Select highest-value task
4. Start execution (status → in_progress)
5. Delegate to specialized team
6. Track execution metrics
7. Update task with results
8. Mark complete
9. Update target progress
10. Send RPC notification
11. Schedule next run if recurring
```

### Tool Update Flow
```
1. New tool added to user_data/tools/
2. ToolRegistry detects file change
3. Reload all tools
4. ToolUpdateService notifies subscribers
5. Teams receive tool updates
6. Tools immediately available to agents
```

---

## Extending SonAgent

### Adding New Tools

Create a Python file in `user_data/tools/`:

```python
# user_data/tools/weather_tool.py

def get_weather(city: str) -> dict:
    """
    Get current weather for a city.
    
    Args:
        city: City name
        
    Returns:
        Weather data dictionary
    """
    return {"city": city, "temp": 72, "condition": "Sunny"}
```

Tool is automatically loaded within 30 seconds and available to all registered teams.

### Custom Task Scheduling

```python
from sonagent.persistence import Task

# Daily at 9 AM
Task.create_task(
    agent_id="system",
    content="Generate daily report",
    cron_expression="0 9 * * *"
)

# Every Monday at 2 PM
Task.create_task(
    agent_id="system",
    content="Weekly summary",
    cron_expression="0 14 * * MON"
)
```

---

## Security Considerations

1. **API Keys**: Store securely in config.json (excluded from git)
2. **Tool Execution**: User-defined tools run with full Python access
3. **Database**: SQLite file permissions should be restricted
4. **RPC Tokens**: JWT tokens for API authentication
5. **GitHub Integration**: Use personal access tokens with minimal scopes

---

## References

- **Agno Framework**: https://agno.build/
- **OpenAI API**: https://platform.openai.com/docs
- **ChromaDB**: https://www.trychroma.com/
- **SQLAlchemy**: https://www.sqlalchemy.org/
- **Telegram Bot API**: https://core.telegram.org/bots/api

---

## Conclusion

SonAgent's architecture provides a flexible, extensible framework for autonomous agent systems. The multi-team coordination model enables specialized handling of diverse tasks, while the dynamic tool system allows runtime capability extension. Combined with persistent memory, task scheduling, and human feedback integration, SonAgent offers a robust platform for digital consciousness backup and autonomous operation.
