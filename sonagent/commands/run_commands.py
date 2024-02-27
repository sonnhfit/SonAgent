import logging
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
            'initial_state': 'running',
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
                "password": "son123"
            },
            'internals': {
                'sd_notify': True
            }
        }

        try:
            config = load_config_file(args['config'][0])
        except Exception as e:
            config = config
            raise OperationalException("Error loading config file: " + str(e))
        # config['user_data_dir'] = args['user_data_dir']
        print(config)

        print(args)
        config['user_data_dir'] = args['user_data_dir']
        worker = Worker(args, config=config)
        worker.run()
    except Exception as e:
        logger.error(str(e))
        logger.exception("Fatal exception!")
    except (KeyboardInterrupt):
        logger.info('SIGINT received, aborting ...')
    finally:
        if worker:
            logger.info("worker found ... calling exit")
            worker.exit()
    return 0
