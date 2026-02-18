import logging
from typing import Dict, List, Any

from sqlalchemy import inspect, text, Column
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


def check_migrate(engine: Engine, decl_base: DeclarativeBase, previous_tables: List[str]) -> None:
    """
    Checks if migration is necessary and migrates if necessary
    """
    inspector = inspect(engine)
    migrating = False
    
    # Check each table in the metadata
    for table_name, table in decl_base.metadata.tables.items():
        if table_name in previous_tables:
            # Table exists, check columns
            existing_columns = {col['name']: col for col in inspector.get_columns(table_name)}
            
            for column in table.columns:
                column_name = column.name
                if column_name not in existing_columns:
                    # Column is missing, add it
                    logger.info(f"Adding missing column '{column_name}' to table '{table_name}'")
                    add_column_sql = get_add_column_sql(engine, table_name, column)
                    try:
                        with engine.begin() as conn:
                            conn.execute(text(add_column_sql))
                        migrating = True
                        logger.info(f"Successfully added column '{column_name}' to table '{table_name}'")
                    except Exception as e:
                        logger.error(f"Failed to add column '{column_name}' to table '{table_name}': {e}")
    
    if migrating:
        logger.info("Database migration finished.")


def get_add_column_sql(engine: Engine, table_name: str, column: Column) -> str:
    """
    Generate SQL to add a column to a table
    """
    # Get the dialect from the engine
    dialect = engine.dialect
    
    # Compile the column type using the dialect
    column_type = column.type.compile(dialect=dialect)
    
    # Build column definition
    column_def = f"{column.name} {column_type}"
    
    # Add NULL/NOT NULL constraint
    if column.nullable:
        column_def += " NULL"
    else:
        column_def += " NOT NULL"
    
    # Add default value if specified
    if column.default is not None:
        if callable(column.default.arg):
            default_value = column.default.arg({})
        else:
            default_value = column.default.arg
        
        if isinstance(default_value, str):
            default_value = f"'{default_value}'"
        column_def += f" DEFAULT {default_value}"
    
    return f"ALTER TABLE {table_name} ADD COLUMN {column_def};"
