"""
Team Registry Models for tracking initialized teams in the system.
"""
import logging
from datetime import datetime
from typing import ClassVar, List, Optional, Dict, Any

from sqlalchemy import Integer, String, DateTime, JSON, select, delete
from sqlalchemy.orm import Mapped, mapped_column

from sonagent.persistence.base import ModelBase, SessionType
from sonagent.utils.datetime_helpers import dt_now

logger = logging.getLogger(__name__)


class TeamRegistry(ModelBase):
    """
    Model for tracking initialized teams in the system.
    
    When the system starts, the registry should be cleared (all records deleted).
    When a team is initialized, a record should be added to register it.
    """
    __tablename__ = "team_registry"
    __allow_unmapped__ = True
    session: ClassVar[SessionType]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=dt_now)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=dt_now, onupdate=dt_now)
    team_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    @staticmethod
    def clear_registry() -> int:
        """
        Clear all records from the team registry.
        Called when the system starts.
        
        Returns:
            Number of records deleted
        """
        try:
            # Delete all records from team_registry table
            result = TeamRegistry.session.execute(delete(TeamRegistry))
            TeamRegistry.session.commit()
            deleted_count = result.rowcount
            logger.info(f"Cleared team registry: deleted {deleted_count} records")
            return deleted_count
        except Exception as e:
            logger.error(f"Error clearing team registry: {e}")
            TeamRegistry.session.rollback()
            return 0

    @staticmethod
    def register_team(
        team_name: str,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        team_metadata: Optional[Dict[str, Any]] = None
    ) -> "TeamRegistry":
        """
        Register a new team in the registry.
        Called when a team is initialized.
        
        Args:
            team_name: Name of the team
            description: Description of the team
            config: Team configuration
            team_metadata: Additional metadata about the team
            
        Returns:
            The created TeamRegistry record
        """
        try:
            team_registry = TeamRegistry(
                team_name=team_name,
                description=description,
                config=config or {},
                team_metadata=team_metadata or {},
                status="active"
            )
            
            TeamRegistry.session.add(team_registry)
            TeamRegistry.session.commit()
            
            logger.info(f"Registered team: {team_name}")
            return team_registry
        except Exception as e:
            logger.error(f"Error registering team {team_name}: {e}")
            TeamRegistry.session.rollback()
            raise

    @staticmethod
    def get_all_teams() -> List["TeamRegistry"]:
        """
        Get all registered teams.
        
        Returns:
            List of all TeamRegistry records
        """
        try:
            return TeamRegistry.session.scalars(
                select(TeamRegistry).order_by(TeamRegistry.created_at.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting all teams: {e}")
            return []

    @staticmethod
    def get_team_by_name(team_name: str) -> Optional["TeamRegistry"]:
        """
        Get a team by its name.
        
        Args:
            team_name: Name of the team to find
            
        Returns:
            TeamRegistry record if found, None otherwise
        """
        try:
            return TeamRegistry.session.scalars(
                select(TeamRegistry).filter(TeamRegistry.team_name == team_name)
            ).first()
        except Exception as e:
            logger.error(f"Error getting team by name {team_name}: {e}")
            return None

    @staticmethod
    def get_teams_by_description_keyword(keyword: str) -> List["TeamRegistry"]:
        """
        Get teams whose description contains a specific keyword.
        
        Args:
            keyword: Keyword to search for in team descriptions
            
        Returns:
            List of TeamRegistry records matching the keyword
        """
        try:
            return TeamRegistry.session.scalars(
                select(TeamRegistry)
                .filter(TeamRegistry.description.contains(keyword))
                .order_by(TeamRegistry.created_at.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting teams by description keyword {keyword}: {e}")
            return []

    @staticmethod
    def update_team_status(team_name: str, status: str) -> Optional["TeamRegistry"]:
        """
        Update the status of a team.
        
        Args:
            team_name: Name of the team to update
            status: New status (e.g., "active", "inactive", "error")
            
        Returns:
            Updated TeamRegistry record if found, None otherwise
        """
        try:
            team = TeamRegistry.get_team_by_name(team_name)
            if team:
                team.status = status
                team.last_updated = dt_now()
                TeamRegistry.session.commit()
                logger.info(f"Updated team {team_name} status to {status}")
                return team
            return None
        except Exception as e:
            logger.error(f"Error updating team {team_name} status: {e}")
            TeamRegistry.session.rollback()
            return None

    @staticmethod
    def update_team_config(team_name: str, config: Dict[str, Any]) -> Optional["TeamRegistry"]:
        """
        Update the configuration of a team.
        
        Args:
            team_name: Name of the team to update
            config: New configuration dictionary
            
        Returns:
            Updated TeamRegistry record if found, None otherwise
        """
        try:
            team = TeamRegistry.get_team_by_name(team_name)
            if team:
                team.config = config
                team.last_updated = dt_now()
                TeamRegistry.session.commit()
                logger.info(f"Updated team {team_name} configuration")
                return team
            return None
        except Exception as e:
            logger.error(f"Error updating team {team_name} configuration: {e}")
            TeamRegistry.session.rollback()
            return None

    @staticmethod
    def get_active_teams() -> List["TeamRegistry"]:
        """
        Get all active teams.
        
        Returns:
            List of active TeamRegistry records
        """
        try:
            return TeamRegistry.session.scalars(
                select(TeamRegistry)
                .filter(TeamRegistry.status == "active")
                .order_by(TeamRegistry.created_at.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting active teams: {e}")
            return []

    @staticmethod
    def get_team_count() -> Dict[str, int]:
        """
        Get counts of teams by status.
        
        Returns:
            Dictionary with team counts by status
        """
        try:
            all_teams = TeamRegistry.get_all_teams()
            total = len(all_teams)
            active = len([t for t in all_teams if t.status == "active"])
            inactive = len([t for t in all_teams if t.status == "inactive"])
            
            return {
                "total": total,
                "active": active,
                "inactive": inactive
            }
        except Exception as e:
            logger.error(f"Error getting team counts: {e}")
            return {"total": 0, "active": 0, "inactive": 0}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the TeamRegistry record to a dictionary.
        
        Returns:
            Dictionary representation of the team registry
        """
        return {
            "id": self.id,
            "team_name": self.team_name,
            "description": self.description,
            "config": self.config or {},
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "metadata": self.team_metadata or {}
        }
