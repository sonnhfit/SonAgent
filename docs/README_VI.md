# SonAgent - Tài liệu tiếng Việt

## Tổng quan

Tài liệu này tóm tắt các cập nhật và thông tin quan trọng về SonAgent - hệ thống Agent tự động cho việc sao lưu ý thức số hóa sử dụng các Mô hình Ngôn ngữ Lớn (LLM). SonAgent là một hệ thống đa agent với kiến trúc team-based, cho phép xử lý các vấn đề phức tạp thông qua sự phối hợp giữa các team chuyên môn.

## Tài liệu chính

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Kiến trúc chi tiết của hệ thống SonAgent
- **[README.MD](../README.MD)** - Hướng dẫn tổng quan và bắt đầu nhanh
- **[install.md](source/install.md)** - Hướng dẫn cài đặt chi tiết
- **[AGENT_SYSTEM.md](AGENT_SYSTEM.md)** - Hệ thống Agent và quản lý Skills
- **[STANDARD_SKILLS.md](STANDARD_SKILLS.md)** - Các Skills tiêu chuẩn
- **[SKILL_BUILDER.md](SKILL_BUILDER.md)** - Hướng dẫn xây dựng Skills

## Chạy SonAgent với Docker

### Sử dụng Docker Image từ GitHub Container Registry

Cách nhanh nhất để chạy SonAgent mà không cần cài đặt Python:

```bash
# Tạo thư mục user_data
mkdir -p user_data

# Tạo file config.json trong user_data với API keys của bạn
# (Xem phần Cấu hình bên dưới)

# Chạy container
docker run -d \
  --name sonagent \
  -v $(pwd)/user_data:/sonagent/user_data \
  -p 8080:8080 \
  ghcr.io/sonnhfit/sonagent/sonagent:latest \
  run \
  --config /sonagent/user_data/config.json \
  --agentdb sqlite:///sonagent/user_data/agentdb.db \
  --memory-url /sonagent/user_data/memory \
  --user-data-dir /sonagent/user_data \
  --log-level info
```

### Các Docker Tags có sẵn

- `ghcr.io/sonnhfit/sonagent/sonagent:latest` - Phiên bản ổn định mới nhất
- `ghcr.io/sonnhfit/sonagent/sonagent:dev` - Phiên bản phát triển mới nhất
- `ghcr.io/sonnhfit/sonagent/sonagent:v1.0.13` - Phiên bản cụ thể

### Sử dụng Docker Compose

```bash
# Clone repository
git clone https://github.com/sonnhfit/SonAgent.git
cd SonAgent

# Tạo user_data và config
mkdir -p user_data
# Tạo user_data/config.json (xem mẫu bên dưới)

# Khởi động
docker-compose up -d

# Xem logs
docker-compose logs -f sonagent

# Dừng
docker-compose down
```

### Cấu hình mẫu (config.json)

```json
{
    "initial_state": "running",
    "timezone": "Asia/Saigon",
    "api_server": {
        "enabled": true,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8080,
        "username": "admin",
        "password": "admin"
    },
    "telegram": {
        "enabled": true,
        "token": "YOUR_TELEGRAM_BOT_TOKEN",
        "chat_id": "YOUR_TELEGRAM_CHAT_ID"
    },
    "openai": {
        "enabled": true,
        "api_type": "openai",
        "api_key": "YOUR_OPENAI_API_KEY"
    },
    "github": {
        "enabled": false,
        "username": "",
        "token": ""
    }
}
```

## Các thành phần chính

### 1. Hệ thống Agent (Agent System)

SonAgent sử dụng kiến trúc đa agent với các thành phần chính:

#### MainTeamAgent
- **Vai trò**: Hub điều phối chính xử lý yêu cầu người dùng
- **Agents con**:
  - **Task Agent**: Quản lý tasks, lịch trình, nhắc nhở
  - **TOM Agent**: Theory of Mind - quản lý beliefs, desires, targets
  - **Feedback Agent**: Xử lý phê duyệt từ con người
  - **Assistant Agent**: Xử lý các truy vấn chung

#### WorkerTeamAgent
- **Vai trò**: Thực thi task tự động
- **Tính năng**:
  - Ưu tiên task dựa trên value score
  - Theo dõi token usage và execution metrics
  - Tự động delegate đến specialized teams
  - Cập nhật tiến độ targets

### 2. Hệ thống Task (Task System)

#### Task Model
Tasks có các thuộc tính:
- **Status**: pending → in_progress → done/failed/cancelled
- **Priority**: 0 (thấp) - 2 (cao)
- **Scheduling**: One-time (`scheduled_at`) hoặc recurring (`cron_expression`)
- **Metrics**: Token usage, execution time, success rate

#### Ví dụ tạo Task

```python
# Task đơn giản
Task.create_task(
    agent_id="user_123",
    content="Nghiên cứu papers AI mới nhất về transformers",
    priority=1
)

# Task định kỳ hàng tuần
Task.create_task(
    agent_id="user_123",
    content="Backup dữ liệu hàng tuần",
    cron_expression="0 2 * * SUN"  # Chủ nhật lúc 2 giờ sáng
)
```

### 3. Worker Architecture

#### Worker Process
- Quản lý vòng đời của SonAgent
- State machine: STOPPED → RUNNING → RELOAD_CONFIG
- Tích hợp systemd cho service management
- Rate control và process throttling

#### SonBot
- Khởi tạo database (SQLAlchemy)
- Tạo MainTeamAgent và WorkerTeamAgent
- Quản lý SkillsManager và ToolRegistry
- Xử lý RPC communication (Telegram, WebSocket, API)

### 4. Tool Registry

#### ToolRegistry
Tự động load và quản lý tools từ `user_data/tools/`:

**Tính năng**:
- Tự động scan thay đổi mỗi 30 giây
- Phát hiện thay đổi dựa trên file hash
- Import module động
- Tự động tạo metadata cho tools

#### Cấu trúc Tool

```python
# user_data/tools/my_tool.py

def calculate_fibonacci(n: int) -> int:
    """
    Tính số Fibonacci thứ n.
    
    Args:
        n: Vị trí trong dãy (bắt đầu từ 0)
        
    Returns:
        Số Fibonacci thứ n
    """
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
```

Tool tự động được load trong vòng 30 giây và có sẵn cho tất cả teams.

### 5. Các team chuyên môn (Specialized Teams)

#### Dev Team (`agents/dev_team.py`)
- **Chức năng**: Phát triển phần mềm, tích hợp GitHub
- **Agents**: Product Owner, Backend Dev, Frontend Dev
- **Use cases**: Triển khai tính năng, sửa bug, refactoring

#### Research Team (`agents/research_team.py`)
- **Chức năng**: Nghiên cứu học thuật và thị trường
- **Agents**: ArXiv Researcher, Wikipedia Researcher, HackerNews Analyst, YFinance Analyst
- **Use cases**: Nghiên cứu papers, phân tích xu hướng, fact-checking

#### Finance Team (`agents/finance_team.py`)
- **Chức năng**: Phân tích tài chính và thị trường
- **Agents**: HackerNews Analyst, Finance Analyst
- **Use cases**: Theo dõi giá cổ phiếu, phân tích công ty, nghiên cứu đầu tư

#### Skills & Tools Team (`agents/skills_and_tools_team.py`)
- **Chức năng**: Tạo tools và skills mới động
- **Khả năng**: 
  - Tạo Python tools trong `user_data/tools/`
  - Tạo Agno skills trong `user_data/skills/`
  - Thực thi Python code để test
  - Chạy shell commands

#### General Task Team (`agents/general_task_team.py`)
- **Chức năng**: Xử lý tasks đa lĩnh vực
- **Tính năng**: Tích hợp động với ToolRegistry, giải quyết vấn đề cross-domain

## Luồng dữ liệu

### User Request Flow
1. User gửi message qua Telegram/API/WebSocket
2. RPC Manager nhận message
3. Chuyển đến SonBot
4. SonBot route đến MainTeamAgent
5. MainTeamAgent phân tích và route đến specialized team
6. Team thực thi task
7. Kết quả lưu vào database
8. Response gửi về user qua RPC
9. Lịch sử chat được lưu trữ

### Autonomous Task Execution Flow
1. WorkerTeamAgent fetch pending tasks
2. Tính value scores
3. Chọn task có value cao nhất
4. Bắt đầu thực thi (status → in_progress)
5. Delegate đến specialized team
6. Theo dõi execution metrics
7. Cập nhật task với kết quả
8. Đánh dấu hoàn thành
9. Cập nhật target progress
10. Gửi RPC notification

## Knowledge Base & Learning

### ChromaDB Vector Store
- OpenAI embeddings cho tri thức persistent
- Collection: "vectors"
- Path: `user_data/chromadb`
- Model: text-embedding-3-small

### Learning Machine
- Mode: AGENTIC
- User profile tracking
- User memory enabled
- Learned knowledge accumulation

## Truy cập API

Khi đã chạy, bạn có thể truy cập:
- **REST API**: http://localhost:8080
- **WebSocket**: ws://localhost:8080/ws
- **API Docs**: http://localhost:8080/docs

## Xử lý sự cố

### Container không khởi động
- Kiểm tra `user_data/config.json` tồn tại và valid JSON
- Kiểm tra port: `lsof -i :8080`
- Xem logs: `docker logs sonagent`

### Permission issues
- Linux: `chmod -R 755 user_data`
- Đảm bảo Docker có quyền truy cập thư mục mounted

### Database errors
- Dừng tất cả instances: `docker stop sonagent`
- Xóa lock files: `rm user_data/agentdb.db-*`
- Khởi động lại: `docker start sonagent`

## Tài nguyên bổ sung

- **GitHub Repository**: https://github.com/sonnhfit/SonAgent
- **Discord Community**: https://discord.gg/XZ8reU9z3T
- **Demo Video**: https://www.youtube.com/watch?v=l_aQ2RG9Np0

## Lưu ý quan trọng

1. **API Keys**: Cần OpenAI API key (khuyến nghị tài khoản trả phí)
2. **Timezone**: Mặc định UTC, có thể đổi sang "Asia/Saigon"
3. **Data Persistence**: Thư mục `user_data` được mount làm volume
4. **Security**: Đảm bảo bảo mật API keys trong config.json
5. **Monitoring**: Theo dõi token usage tại https://platform.openai.com/usage

---

**Phiên bản**: 1.0.13  
**Cập nhật**: 2024  
**Tác giả**: Son Nguyen Huu
