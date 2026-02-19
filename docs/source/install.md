# Setting up SonAgent
**📋 Requirements:**

Choose an environment to run SonAgent in (pick one):

•	[Docker](#running-with-docker) (recommended for easy setup)

•	Python 3.11 or later [(opens in a new tab)](https://www.tutorialspoint.com/how-to-install-python-in-windows)


**🗝️ Getting an API key:**


Get your OpenAI API key from: OpenAI [(opens in a new tab)](https://platform.openai.com/account/api-keys)

**⚠️ Attention:**

* To use the OpenAI API with SonAgent, we strongly recommend setting up billing (AKA paid account). Free accounts are [limited](https://platform.openai.com/docs/guides/rate-limits/overview?context=tier-free) to 3 API calls per minute, which can cause the application to crash.
You can set up a paid account at [Manage account > Billing > Overview](https://platform.openai.com/account/billing/overview)
## Quick Start 

### 1. Install Dependencies

```
pip install sonagent
```

### 2. Run agent

- 2.1 create `user_data` folder that will save agent skill, and user database
```
sonagent init
```
- 2.2 Please fill in the API key of openai, telegram, and github if you want the agent to create a pull request in the `user_data/config.json` file
- 2.3 run agent with file path param from step 2.1
```
sonagent run \
--config ./user_data/config.json \
--agentdb sqlite:///user_data/agentdb.sqlite \
--memory-url ./user_data/memory \
--datadir ./user_data/ \
--user-data-dir ./user_data/
```


**🚀 Important:**

It's highly recommended that you keep keep track of your API costs on the [Usage page](https://platform.openai.com/usage). You can also set limits on how much you spend on the [Usage limits page](https://platform.openai.com/account/limits).
 
## Configuration

To install the latest version and understand more about installation details. follow step bellow 

1. Clone the SonAgent repository from GitHub using the command:

   ```
   git clone https://github.com/sonnhfit/SonAgent.git
   ```
   
3. Navigate to the cloned directory:
   
   ```
   cd SonAgent
   ```
   
5. Create a new Python environment using conda with the specified version:
   
   ```
   conda create --name SonAgentenv python=3.11
   ```
   
7. Activate the newly created environment:
   
   ```
   conda activate SonAgentenv
   ```
   
9. Install the package manager pip within the conda environment:
    
   ```
   conda install pip
   ```
   
11. Install all the required dependencies listed in the requirements.txt file:

   ```
   pip install -r requirements.txt
   ```

13. Install the SonAgent package in editable mode to allow changes:
    
   ```
   pip install --editable .
   ```

15. To run SonAgent, use the following command with the appropriate configurations:
    
   ```
   sonagent run --config /path/to/user_data/config.json --agentdb sqlite:///user_data/myagentdb.sqlite --memory-url /path/to/user_data/memory --datadir /path/to/user_data/  --user-data-dir /path/to/user_data/
   ```
Remember to replace placeholder text such as path/to with your actual path to the SonAgent folder you clone from git.

**🛠️ Setup the configuration file:**

To get the agent up and run, you need to insert OpenAi key and the chatbot key in order to communicate with the agent. In this case, we recommend BotFather from telegram for easier adoption:
1.	Navigate to the **user_data** folder within your SonAgent project directory.
2.	Locate the **config.json** file. If it does not exist, create a new text file and name it **config.json**.
3.	Open the **config.json** file in a text editor of your choice.
4.	Copy and paste the provided JSON structure into your **config.json** file:

```{
    "initial_state": "running",
    "timezone": "UTC",
    "api_server": {
        "enabled": true,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8080,
        "verbosity": "error",
        "enable_openapi": true,
        "jwt_secret_key": "secret",
        "ws_token": "4IvjuMcs3MsVRYcMcl-3UXfZuWX3oNvbrQ",
        "CORS_origins": [],
        "username": "admin",
        "password": "admin"
    },
    "internals": {
        "sd_notify": true
    },
    "telegram": {
        "enabled": true,
        "token": " your_telegram_bot_token_here",
        "chat_id": " your_telegram_user_id_here"
    },
    "openai": {
        "enabled": true,
        "api_type": "openai",
        "api_key": " your_openai_api_key_here"
    },
    "skills_file_path": "skills/skills.yaml",
    "github": {
        "enabled": false,
        "username": "sonnhfit",
        "repo_name": "SonAgent",
        "token": "",
        "local_repo_path": ""
    }
}
```

**Timezone Configuration:**
You can configure the agent's timezone by adding a `timezone` field to your config.json (default is "UTC"). For example:
```json
{
    "timezone": "Asia/Saigon",
    // ... other settings
}
```

Alternatively, you can set the `SONAGENT_TIMEZONE` environment variable (overrides config file):
```bash
export SONAGENT_TIMEZONE="America/New_York"
```

Supported timezones: Any valid timezone string (e.g., "UTC", "Asia/Saigon", "America/New_York", "Europe/London").

By following these steps, your config.json file should be properly set up with your OpenAI API key and Telegram bot information. Remember to replace placeholder text such as **your_openai_api_key_here**, **your_telegram_bot_token_here**, and **your_telegram_user_id_here** with your actual credentials.

**🎊 Running SonAgent:**

Simply run the startup script in your terminal. This will install any necessary Python packages and launch SonAgent.
1.	Navigate to the cloned directory:

   ```
  	cd SonAgent
```

2.	Activate the newly created environment:
   
   ```
  	conda activate SonAgentenv
```

3.	Init SonAgent:
   
```
sonagent run \
--config /path/to/user_data/config.json \
--agentdb sqlite:///user_data/myagentdb.sqlite \
--memory-url /path/to/user_data/memory \
--datadir /path/to/user_data/  \
--user-data-dir /path/to/user_data/ 
```

Make sure you have a compatible Python version installed. See also the [requirements](../requirements.txt)

---

## Running with Docker

Docker provides an easy way to run SonAgent without installing Python dependencies manually.

### Prerequisites

- Docker installed on your system ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose (included with Docker Desktop)

### Using Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sonnhfit/SonAgent.git
   cd SonAgent
   ```

2. **Create user_data directory**:
   ```bash
   mkdir -p user_data
   ```

3. **Create configuration file**:
   
   Create `user_data/config.json` with your API keys:
   ```json
   {
       "initial_state": "running",
       "timezone": "UTC",
       "api_server": {
           "enabled": true,
           "listen_ip_address": "0.0.0.0",
           "listen_port": 8080,
           "verbosity": "error",
           "enable_openapi": true,
           "jwt_secret_key": "your_secret_key_here",
           "ws_token": "your_ws_token_here",
           "CORS_origins": [],
           "username": "admin",
           "password": "admin"
       },
       "telegram": {
           "enabled": true,
           "token": "your_telegram_bot_token_here",
           "chat_id": "your_telegram_user_id_here"
       },
       "openai": {
           "enabled": true,
           "api_type": "openai",
           "api_key": "your_openai_api_key_here"
       },
       "github": {
           "enabled": false,
           "username": "your_github_username",
           "repo_name": "SonAgent",
           "token": "",
           "local_repo_path": ""
       }
   }
   ```

4. **Create environment file** (optional):
   
   Copy `example.env` to `.env` and customize:
   ```bash
   cp example.env .env
   # Edit .env with your preferred settings
   ```

5. **Run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

6. **View logs**:
   ```bash
   docker-compose logs -f sonagent
   ```

7. **Stop the agent**:
   ```bash
   docker-compose down
   ```

### Using Pre-built Docker Image

You can also run SonAgent directly using the pre-built image from GitHub Container Registry:

```bash
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

**Note**: Make sure you have created `user_data/config.json` before running the container.

### Available Docker Tags

The CI automatically builds and pushes Docker images to GitHub Container Registry:

- `ghcr.io/sonnhfit/sonagent/sonagent:latest` - Latest build from main branch
- `ghcr.io/sonnhfit/sonagent/sonagent:dev` - Latest build from dev branch
- `ghcr.io/sonnhfit/sonagent/sonagent:v1.0.13` - Specific version tags
- `ghcr.io/sonnhfit/sonagent/sonagent:sha-abc123` - Specific commit SHA

### Building Docker Image Locally

If you want to build the Docker image yourself:

```bash
docker build -t sonagent:latest .
```

Then run it:
```bash
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

### Docker Volume Persistence

The `user_data` directory is mounted as a volume, which ensures:
- Your configuration persists across container restarts
- Agent database and memory are preserved
- Custom tools and skills are maintained
- Logs are accessible from the host system

### Accessing the API

Once running, you can access:
- **REST API**: http://localhost:8080
- **WebSocket**: ws://localhost:8080/ws
- **OpenAPI docs**: http://localhost:8080/docs (if enabled in config)

### Troubleshooting Docker

**Container won't start:**
- Check if config.json exists and is valid JSON
- Verify port 8080 is not already in use: `lsof -i :8080`
- Check logs: `docker logs sonagent`

**Permission issues:**
- Ensure user_data directory has correct permissions
- On Linux: `chmod -R 755 user_data`

**Database locked errors:**
- Stop any other instances accessing the database
- Remove lock files: `rm user_data/agentdb.db-*`
