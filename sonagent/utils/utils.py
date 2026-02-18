import hashlib
import logging
import os

logger = logging.getLogger(__name__)


def read_text_from_file(file_path: str) -> str:
    f = open(file_path, "r")
    f.close()
    return f.read()


def hash_str(string: str) -> str:
    sha = hashlib.sha256()
    sha.update(string.encode())
    return sha.hexdigest()


def hash_md5_str(string: str) -> str:
    m = hashlib.md5(string.encode('UTF-8'))
    return m.hexdigest()


def get_schema_from_dict(data: dict) -> dict:
    schema = {}
    for key, value in data.items():
        if isinstance(value, dict):
            schema[key] = get_schema_from_dict(value)
        else:
            schema[key] = type(value).__name__
    return schema


def init_evironment():
    try:
        from sonagent.persistence.models import Environment
        logger.info("Initializing environment ...")
        envs = Environment.get_all_environment()
        for env in envs:
            os.environ[str(env.key)] = str(env.value)

        logger.debug(os.environ)
    except Exception as e:
        logger.error(f"Error initializing environment: {e}")
        raise e


def init_team_registry(db_url: str) -> None:
    """
    Initialize team registry on system startup.
    Clears all existing team records and prepares for new team registrations.
    
    Args:
        db_url: Database URL for team registry
    """
    try:
        from sonagent.persistence.team_registry_models import TeamRegistry
        from sqlalchemy.orm import scoped_session, sessionmaker
        from sqlalchemy import create_engine
        
        logger.info("Initializing team registry...")
        
        # Create engine and session for TeamRegistry
        engine = create_engine(db_url, future=True)
        TeamRegistry.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
        TeamRegistry.query = TeamRegistry.session.query_property()
        
        # Clear the registry
        deleted_count = TeamRegistry.clear_registry()
        logger.info(f"Cleared team registry on startup: deleted {deleted_count} records")
        
    except Exception as e:
        logger.error(f"Error initializing team registry: {e}")
        raise e


def register_team_in_registry(
    team_name: str,
    description: str,
    db_url: str,
    config: dict = None,
    team_metadata: dict = None
) -> dict:
    """
    Register a team in the team registry.
    
    Args:
        team_name: Name of the team
        description: Description of the team
        db_url: Database URL for team registry
        config: Team configuration
        team_metadata: Additional metadata
        
    Returns:
        Dictionary with registration result
    """
    try:
        from sonagent.persistence.team_registry_models import TeamRegistry
        from sqlalchemy.orm import scoped_session, sessionmaker
        from sqlalchemy import create_engine
        from sonagent.utils.datetime_helpers import dt_now
        
        logger.info(f"Registering team '{team_name}' in registry...")
        
        # Create engine and session for TeamRegistry
        engine = create_engine(db_url, future=True)
        TeamRegistry.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
        TeamRegistry.query = TeamRegistry.session.query_property()
        
        # Register the team
        team_registry = TeamRegistry.register_team(
            team_name=team_name,
            description=description,
            config=config or {},
            team_metadata=team_metadata or {}
        )
        
        logger.info(f"Successfully registered team: {team_name}")
        
        return {
            "success": True,
            "team_id": team_registry.id,
            "team_name": team_registry.team_name,
            "message": f"Team '{team_name}' registered successfully"
        }
        
    except Exception as e:
        logger.error(f"Error registering team '{team_name}': {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to register team '{team_name}'"
        }


def get_registered_teams(db_url: str, active_only: bool = True) -> list:
    """
    Get all registered teams from the registry.
    
    Args:
        db_url: Database URL for team registry
        active_only: Whether to return only active teams
        
    Returns:
        List of team dictionaries
    """
    try:
        from sonagent.persistence.team_registry_models import TeamRegistry
        from sqlalchemy.orm import scoped_session, sessionmaker
        from sqlalchemy import create_engine
        
        # Create engine and session for TeamRegistry
        engine = create_engine(db_url, future=True)
        TeamRegistry.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
        TeamRegistry.query = TeamRegistry.session.query_property()
        
        if active_only:
            teams = TeamRegistry.get_active_teams()
        else:
            teams = TeamRegistry.get_all_teams()
        
        return [team.to_dict() for team in teams]
        
    except Exception as e:
        logger.error(f"Error getting registered teams: {e}")
        return []


def get_team_registry_stats(db_url: str) -> dict:
    """
    Get statistics about the team registry.
    
    Args:
        db_url: Database URL for team registry
        
    Returns:
        Dictionary with team registry statistics
    """
    try:
        from sonagent.persistence.team_registry_models import TeamRegistry
        from sqlalchemy.orm import scoped_session, sessionmaker
        from sqlalchemy import create_engine
        
        # Create engine and session for TeamRegistry
        engine = create_engine(db_url, future=True)
        TeamRegistry.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
        TeamRegistry.query = TeamRegistry.session.query_property()
        
        stats = TeamRegistry.get_team_count()
        
        return {
            "success": True,
            "stats": stats,
            "message": f"Team registry statistics retrieved"
        }
        
    except Exception as e:
        logger.error(f"Error getting team registry stats: {e}")
        return {
            "success": False,
            "error": str(e),
            "stats": {"total": 0, "active": 0, "inactive": 0}
        }
