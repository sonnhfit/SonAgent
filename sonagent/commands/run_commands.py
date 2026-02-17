import logging
import os
import signal
from typing import Any, Dict

from sonagent.configuration import load_config_file
from sonagent.exceptions import OperationalException

logger = logging.getLogger(__name__)


def start_sonagent(args: Dict[str, Any]) -> int:
    """
    Main entry point for running mode
    """
    # Import here to avoid loading worker module when it's not used
    from sonagent.worker import Worker

    def term_handler(signum, frame):
        # Raise KeyboardInterrupt - so we can handle it in the same way as Ctrl-C
        raise KeyboardInterrupt()

    # Create and run worker
    worker = None
    try:
        signal.signal(signal.SIGTERM, term_handler)

        config = {
            "initial_state": "running",
            "api_server": {
                "enabled": True,
                "listen_ip_address": "0.0.0.0",
                "listen_port": 8080,
                "verbosity": "error",
                "enable_openapi": True,
                "jwt_secret_key": "secret",
                "ws_token": "4IvjuMcs3MsVRYcMcl-3UXfZuWX3oNvbrQ",
                "CORS_origins": [],
                "username": "sonnh",
                "password": "son123",
            },
            "internals": {"sd_notify": True},
        }

        try:
            config = load_config_file(args["config"][0])
        except Exception as e:
            config = config
            raise OperationalException("Error loading config file: " + str(e))
        # config['user_data_dir'] = args['user_data_dir']

        # Set user_data_dir from args, default to 'user_data' if not provided
        user_data_dir = args.get("user_data_dir")
        if user_data_dir is None:
            user_data_dir = "user_data"
        config["user_data_dir"] = user_data_dir
        worker = Worker(args, config=config)
        worker.run()
    except Exception as e:
        logger.error(str(e))
        logger.exception("Fatal exception!")
    except KeyboardInterrupt:
        logger.info("SIGINT received, aborting ...")
    finally:
        if worker:
            logger.info("worker found ... calling exit")
            worker.exit()
    return 0


def create_user_data_dir(args: Dict[str, Any]) -> None:
    """
    Create user data directory
    """
    print("Creating user data directory")
    current_path = str(os.getcwd())
    user_data_dir = args.get("user_data_dir")
    
    # Set default user_data_dir if not provided
    if user_data_dir is None:
        user_data_dir = "user_data"
    
    print(f"Creating directory: {current_path}/{user_data_dir}")
    
    # Create main user data directory if it doesn't exist
    user_data_path = os.path.join(current_path, user_data_dir)
    if not os.path.exists(user_data_path):
        os.makedirs(user_data_path)
        print(f"Created directory: {user_data_path}")
    
    # Create skills subdirectory if it doesn't exist
    skills_path = os.path.join(user_data_path, "skills")
    if not os.path.exists(skills_path):
        os.makedirs(skills_path)
        print(f"Created skills directory: {skills_path}")
    
    # Note: We no longer create skills.yaml file since skills are loaded dynamically from the directory

    # Create config.json file with default configuration
    config_example = """
{
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
        "token": "",
        "chat_id": ""
    },
    "llm": {
        "enabled": true,
        "api_type": "openai",
        "api_key": "",
        "params": {
            "model": "gpt-4o-mini",
            "temperature": 0.5,
            "max_tokens": 100,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }
    },
    "vector_memory": {
        "type": "file",
        "path": "memory",
        "collection": "memory",
        "host": "localhost",
        "port": 8000,
        "embedding": "openai"
    },
    "github": {
        "enabled": false,
        "username": "sonnhfit",
        "repo_name": "SonAgent",
        "token": "",
        "local_repo_path": ""
    },
    "webhook": {
        "enabled": false,
        "url": "",
        "chat": {
            "message": "{message}"
        }
    }
}
"""
    
    config_file_path = os.path.join(user_data_path, "config.json")
    with open(config_file_path, "w") as file:
        file.write(config_example)
    
    print(f"Created config file: {config_file_path}")
    logger.info(f"[DONE] User data directory created at {user_data_path}")
    return None
