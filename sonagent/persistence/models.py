import logging

from typing import Any, Dict, Final, Optional

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import NoSuchModuleError
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from sonagent.exceptions import OperationalException
from sonagent.persistence.base import ModelBase
from sonagent.persistence.migrations import check_migrate
from sonagent.persistence.belief_models import Belief

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
    
    try:
        previous_tables = inspect(engine).get_table_names()
    except Exception as e:
        print("okii")
    
    ModelBase.metadata.create_all(engine)

    print("run here")
    check_migrate(engine, decl_base=ModelBase, previous_tables=previous_tables)
