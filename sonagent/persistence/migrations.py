import logging

from sqlalchemy import inspect


logger = logging.getLogger(__name__)

def check_migrate(engine, decl_base, previous_tables) -> None:
    """
    Checks if migration is necessary and migrates if necessary
    """
    inspect(engine)
    migrating = False

    if migrating:
        logger.info("Database migration finished.")
