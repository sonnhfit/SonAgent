# Setting up SonAgent
**📋 Requirements:**

Choose an environment to run SonAgent in (pick one):

•	Docker (opens in a new tab) (coming soon)

•	Python 3.11 or later [(opens in a new tab)](https://www.tutorialspoint.com/how-to-install-python-in-windows)


**🗝️ Getting an API key**

Get your OpenAI API key from: OpenAI [(opens in a new tab)](https://platform.openai.com/account/api-keys)

**⚠️ Attention**

* To use the OpenAI API with SonAgent, we strongly recommend setting up billing (AKA paid account). Free accounts are [limited](https://platform.openai.com/docs/guides/rate-limits/overview?context=tier-free) to 3 API calls per minute, which can cause the application to crash.
You can set up a paid account at [Manage account > Billing > Overview](https://platform.openai.com/account/billing/overview)

**Important**
It's highly recommended that you keep keep track of your API costs on the [Usage page](https://platform.openai.com/usage). You can also set limits on how much you spend on the [Usage limits page](https://platform.openai.com/account/limits).
 
**Configuration**
Warning
We recommend to use Git or Docker, to make updating easier.

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

Remember to replace placeholder text such as path/to with your actual path to the SonAgent folder you clone from git
Setup the configuration file:
To get the agent up and run, you need to insert OpenAi key and the chatbot key in order to communicate with the agent. In this case, we recommend BotFather from telegram for easier adoption:
1.	Navigate to the **user_data** folder within your SonAgent project directory.
2.	Locate the **config.json** file. If it does not exist, create a new text file and name it **config.json**.
3.	Open the **config.json** file in a text editor of your choice.
4.	Copy and paste the provided JSON structure into your **config.json** file:
```{
    "initial_state": "running",
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
By following these steps, your config.json file should be properly set up with your OpenAI API key and Telegram bot information. Remember to replace placeholder text such as **your_openai_api_key_here**, **your_telegram_bot_token_here**, and **your_telegram_user_id_here** with your actual credentials.

**Running SonAgent**
Simply run the startup script in your terminal. This will install any necessary Python packages and launch SonAgent.
1.	Navigate to the cloned directory:
   ```
  	cd SonAgent
```
3.	Activate the newly created environment:
   ```
  	conda activate SonAgentenv
```
5.	Init SonAgent:
```
sonagent run --config /path/to/user_data/config.json --agentdb sqlite:///user_data/myagentdb.sqlite --memory-url /path/to/user_data/memory --datadir /path/to/user_data/  --user-data-dir /path/to/user_data/
```
Make sure you have a compatible Python version installed. See also the requirements.
