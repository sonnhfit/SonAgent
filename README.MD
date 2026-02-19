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
- 2.2 Please fill in the API key of openai, telegram, and github if you want the agent to create a pull request in the `user_data/config.json` file. You can also configure the timezone for the agent (default is UTC).
- 2.3 run agent with file path param from step 2.1

**Note:** On first run, standard skills (TextPrinter, WeatherAPISkill, HanoiWeatherChecker, SkillBuilder) are automatically copied to `user_data/skills/`. You can customize or remove these as needed. See [Standard Skills Documentation](docs/STANDARD_SKILLS.md) for more details.
```
sonagent run 
--config /path/to/user_data/config.json 
--agentdb sqlite:///user_data/myagentdb.sqlite 
--memory-url /path/to/user_data/memory 
--datadir /path/to/user_data/  
--user-data-dir /path/to/user_data/
```
for example:

```
sonagent run --config user_data/config.json --agentdb sqlite:///user_data/agentdb.db --memory-url user_data/memory --user-data-dir user_data --log-level info
```
#### 3. Configuration

The agent supports timezone configuration for datetime operations. You can configure timezone in two ways:

1. **Via config.json file**: Add a `timezone` field to your `user_data/config.json`:
```json
{
    "timezone": "Asia/Saigon",
    "api_server": {
        // ... other settings
    }
}
```

2. **Via environment variable**: Set `SONAGENT_TIMEZONE` environment variable (overrides config file):
```bash
export SONAGENT_TIMEZONE="America/New_York"
# or when running:
SONAGENT_TIMEZONE="Europe/London" sonagent run --config user_data/config.json ...
```

**Priority**: Environment variable > Config file > Default (UTC)

**Supported timezones**: Any valid timezone string supported by pytz (e.g., "UTC", "Asia/Saigon", "America/New_York", "Europe/London").

#### 4. check rpc channal  

```
```


### Dev

```
pip install --editable .
```

### Docker

Docker provides the easiest way to run SonAgent without managing Python dependencies.

#### Prerequisites

- Docker installed on your system ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose (included with Docker Desktop)

#### Quick Start with Docker Compose (Recommended)

1. **Clone the repository**:
```bash
git clone https://github.com/sonnhfit/SonAgent.git
cd SonAgent
```

2. **Create user_data directory**:
```bash
mkdir -p user_data
```

3. **Create configuration file** (`user_data/config.json`):
```json
{
    "initial_state": "running",
    "timezone": "UTC",
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

4. **(Optional) Create `.env` file** for environment variables:
```bash
cp example.env .env
# Edit .env with your preferred settings
```

5. **Start SonAgent**:
```bash
docker-compose up -d
```

6. **View logs**:
```bash
docker-compose logs -f sonagent
```

7. **Stop SonAgent**:
```bash
docker-compose down
```

#### Using Pre-built Docker Image

Run directly from GitHub Container Registry without cloning:

```bash
# Create user_data directory and config first
mkdir -p user_data
# Create user_data/config.json with your API keys

# Run the container
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

#### Available Docker Tags

Pre-built images are automatically published to GitHub Container Registry:

- `ghcr.io/sonnhfit/sonagent/sonagent:latest` - Latest stable release from main branch
- `ghcr.io/sonnhfit/sonagent/sonagent:dev` - Latest development build from dev branch
- `ghcr.io/sonnhfit/sonagent/sonagent:v1.0.13` - Specific version tags
- `ghcr.io/sonnhfit/sonagent/sonagent:sha-abc123` - Specific commit builds

#### Building Docker Image Locally

If you want to build the image yourself:

```bash
# Build the image
docker build -t sonagent:latest .

# Run your custom build
docker run -d \
  --name sonagent \
  -v $(pwd)/user_data:/sonagent/user_data \
  -p 8080:8080 \
  sonagent:latest \
  run \
  --config /sonagent/user_data/config.json \
  --agentdb sqlite:///sonagent/user_data/agentdb.db \
  --memory-url /sonagent/user_data/memory \
  --user-data-dir /sonagent/user_data \
  --log-level info
```

#### Docker Features

**Persistent Data**: The `user_data` directory is mounted as a volume, ensuring:
- Configuration persists across restarts
- Database and memory are preserved
- Custom tools and skills are maintained
- Logs are accessible from host

**API Access**: Once running, access:
- **REST API**: http://localhost:8080
- **WebSocket**: ws://localhost:8080/ws
- **API Docs**: http://localhost:8080/docs (if enabled)

#### Docker Troubleshooting

**Container won't start:**
- Verify `user_data/config.json` exists and is valid JSON
- Check port availability: `lsof -i :8080`
- View logs: `docker logs sonagent`

**Permission issues:**
- Linux: `chmod -R 755 user_data`
- Ensure Docker has access to the mounted directory

**Database errors:**
- Stop all instances: `docker stop sonagent`
- Remove lock files: `rm user_data/agentdb.db-*`
- Restart: `docker start sonagent`

## Contributors
A big thank you to all the contributors who helped improve this project. 
- Thank you from the freqtrade community, i learned a lot during my time contributing to it
- @kkmeansnt has made major contributions to documentation as well as testing
- Another colleague i learned a lot of interesting things from him, I know about autogen through him. thank @trungtv
- And other contributors in the [contribute tab](https://github.com/sonnhfit/SonAgent/graphs/contributors) 
- And you who have been paying attention, users and error reporting.



