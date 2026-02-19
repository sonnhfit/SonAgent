import logging
import os
import signal
from typing import Any, Dict

from sonagent.configuration import load_config_file, export_api_keys_to_env
from sonagent.exceptions import OperationalException
from sonagent.loggers import setup_logging

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
            # Set SONAGENT_CONFIG environment variable so datetime helpers can find the config
            config_path = args["config"][0]
            os.environ['SONAGENT_CONFIG'] = config_path
            
            config = load_config_file(config_path)
            # Export API keys from config to environment variables
            export_api_keys_to_env(config)
        except Exception as e:
            config = config
            raise OperationalException("Error loading config file: " + str(e))
        # config['user_data_dir'] = args['user_data_dir']

        # Set user_data_dir from args, default to 'user_data' if not provided
        user_data_dir = args.get("user_data_dir")
        if user_data_dir is None:
            user_data_dir = "user_data"
        config["user_data_dir"] = user_data_dir
        
        # Export user_data_dir as environment variable for easy access
        os.environ['SONAGENT_USER_DATA_DIR'] = user_data_dir
        logger.info(f"Set SONAGENT_USER_DATA_DIR environment variable to: {user_data_dir}")
        
        # Add command line arguments to config for logging
        config["verbosity"] = args.get("verbosity", 0)
        config["log_level"] = args.get("log_level", "info")
        config["logfile"] = args.get("logfile")
        
        # Setup logging with config
        setup_logging(config)
        
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
    Create user data directory with all required subdirectories
    """
    print("Creating user data directory")
    current_path = str(os.getcwd())
    user_data_dir = args.get("user_data_dir")
    
    # Set default user_data_dir if not provided
    if user_data_dir is None:
        user_data_dir = "user_data"
    
    # Export user_data_dir as environment variable for easy access
    os.environ['SONAGENT_USER_DATA_DIR'] = user_data_dir
    print(f"Set SONAGENT_USER_DATA_DIR environment variable to: {user_data_dir}")
    
    print(f"Creating directory: {current_path}/{user_data_dir}")
    
    # Create main user data directory if it doesn't exist
    user_data_path = os.path.join(current_path, user_data_dir)
    if not os.path.exists(user_data_path):
        os.makedirs(user_data_path)
        print(f"Created directory: {user_data_path}")
    
    # Define all required subdirectories
    subdirs = [
        "agents",
        "memory", 
        "skills",
        "tools",
        "workflows",
        "workspace"
    ]
    
    # Create all subdirectories
    for subdir in subdirs:
        subdir_path = os.path.join(user_data_path, subdir)
        if not os.path.exists(subdir_path):
            os.makedirs(subdir_path)
            print(f"Created {subdir} directory: {subdir_path}")
            
            # Add .gitkeep file to empty directories
            gitkeep_file = os.path.join(subdir_path, '.gitkeep')
            if not os.path.exists(gitkeep_file):
                with open(gitkeep_file, 'w') as f:
                    f.write('')
                print(f"  Added .gitkeep to {subdir} directory")
        else:
            print(f"{subdir} directory already exists: {subdir_path}")
    
    # Note: We no longer create skills.yaml file since skills are loaded dynamically from the directory

    # Create config.json file with default configuration
    config_example = """{
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
    if not os.path.exists(config_file_path):
        with open(config_file_path, "w") as file:
            file.write(config_example)
        print(f"Created config file: {config_file_path}")
    else:
        print(f"Config file already exists: {config_file_path}")
    
    logger.info(f"[DONE] User data directory created at {user_data_path}")
    print(f"\n✅ User data directory setup complete at: {user_data_path}")
    print("   Subdirectories created: agents, memory, skills, tools, workflows, workspace")
    print("   Default config.json created")
    print("\nYou can now add your tools to the user_data/tools/ directory")
    return None
