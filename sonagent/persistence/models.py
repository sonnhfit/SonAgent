import logging
from typing import Any, Dict

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from sonagent.exceptions import OperationalException
from sonagent.persistence.base import ModelBase
from sonagent.persistence.belief_models import Belief
from sonagent.persistence.chat_models import ChatMessage, Conversation
from sonagent.persistence.environment_models import Environment
from sonagent.persistence.migrations import check_migrate
from sonagent.persistence.tasks_models import Task, Target
from sonagent.persistence.team_registry_models import TeamRegistry

logger = logging.getLogger(__name__)

_SQL_DOCS_URL = 'http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls'


def init_db(db_url: str) -> None:
    """
    Initializes this module with the given config,
    registers all known command handlers
    and starts polling for message updates
    :param db_url: Database to use
    :return: None
    """
    kwargs: Dict[str, Any] = {}



    if db_url == 'sqlite:///':
        raise OperationalException(
            f'Bad db-url {db_url}. For in-memory database, please use `sqlite://`.')
    if db_url == 'sqlite://':
        kwargs.update({
            'poolclass': StaticPool,
        })
    # Take care of thread ownership
    if db_url.startswith('sqlite://'):
        kwargs.update({
            'connect_args': {'check_same_thread': False},
        })

    engine = create_engine(db_url, future=True, **kwargs)

    Belief.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
    Belief.query = Belief.session.query_property()

    Environment.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
    Environment.query = Environment.session.query_property()

    Task.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
    Task.query = Task.session.query_property()

    ChatMessage.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
    ChatMessage.query = ChatMessage.session.query_property()

    Conversation.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
    Conversation.query = Conversation.session.query_property()

    TeamRegistry.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
    TeamRegistry.query = TeamRegistry.session.query_property()

    Target.session = scoped_session(sessionmaker(bind=engine, autoflush=False))
    Target.query = Target.session.query_property()

    
    try:
        previous_tables = inspect(engine).get_table_names()
    except Exception as e:
        logger.error(f"Error inspecting tables: {e}")
    
    ModelBase.metadata.create_all(engine)

    check_migrate(engine, decl_base=ModelBase, previous_tables=previous_tables)
