"""
Export API keys from configuration to environment variables.
"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def export_api_keys_to_env(config: Dict[str, Any]) -> None:
    """
    Export API keys from configuration to environment variables.
    
    This function extracts API keys and tokens from the configuration
    and sets them as environment variables for use by various components.
    
    Args:
        config: Configuration dictionary loaded from config.json
    """
    try:
        # Export OpenAI API key if present
        llm_config = config.get('llm', {})
        if llm_config.get('api_type') == 'openai':
            api_key = llm_config.get('api_key')
            if api_key:
                os.environ['OPENAI_API_KEY'] = api_key
                logger.debug("Exported OPENAI_API_KEY to environment")
        
        # Export GitHub token if present
        github_config = config.get('github', {})
        if github_config.get('enabled', False):
            github_token = github_config.get('token')
            if github_token:
                os.environ['GITHUB_TOKEN'] = github_token
                logger.debug("Exported GITHUB_TOKEN to environment")
        
        # Export Telegram token if present
        telegram_config = config.get('telegram', {})
        if telegram_config.get('enabled', False):
            telegram_token = telegram_config.get('token')
            if telegram_token:
                os.environ['TELEGRAM_TOKEN'] = telegram_token
                logger.debug("Exported TELEGRAM_TOKEN to environment")
        
        # Export JWT secret key if present
        api_server_config = config.get('api_server', {})
        jwt_secret = api_server_config.get('jwt_secret_key')
        if jwt_secret and jwt_secret not in ('super-secret', 'secret'):
            os.environ['JWT_SECRET_KEY'] = jwt_secret
            logger.debug("Exported JWT_SECRET_KEY to environment")
        
        # Export webhook URL if present
        webhook_config = config.get('webhook', {})
        if webhook_config.get('enabled', False):
            webhook_url = webhook_config.get('url')
            if webhook_url:
                os.environ['WEBHOOK_URL'] = webhook_url
                logger.debug("Exported WEBHOOK_URL to environment")
        
        logger.info("API keys exported to environment variables")
        
    except Exception as e:
        logger.error(f"Error exporting API keys to environment: {e}")
        raise