import logging
from typing import List, Optional

from sqlalchemy import inspect, select, text, tuple_, update

from sonagent.persistence.belief_models import Belief
from sonagent.persistence.planning_models import Plan
from sonagent.persistence.skill_models import SkillDocs

logger = logging.getLogger(__name__)

def check_migrate(engine, decl_base, previous_tables) -> None:
    """
    Checks if migration is necessary and migrates if necessary
    """
    inspector = inspect(engine)
    migrating = False

    if migrating:
        logger.info("Database migration finished.")
