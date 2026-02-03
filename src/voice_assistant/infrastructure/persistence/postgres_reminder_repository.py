"""
PostgreSQL implementation of reminder repository.
Implements IReminderRepository with asyncpg and date range queries.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""
import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import asyncpg

from ...domain.repositories.reminder_repository import IReminderRepository
from ...domain.entities.reminder import Reminder
from .database_connection import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class PostgresReminderRepository(IReminderRepository):
    """
    PostgreSQL implementation of reminder repository.
    
    Implements repository pattern with:
    - Connection pooling via DatabaseConnectionPool
    - Date range queries for efficient filtering
    - Transaction support for complex operations
    """
    
    def __init__(self, db_pool: DatabaseConnectionPool):
        self._db_pool = db_pool
        self._table_name = "reminders"
    
    async def get_by_session(
        self,
        session_id: UUID,
        date_range_start: Optional[datetime] = None,
        date_range_end: Optional[datetime] = None
    ) -> List[Reminder]:
        """
        Get reminders by session ID with optional date range filtering.
        Uses index on reminder_date for efficient queries.
        """
        try:
            async with self._db_pool.acquire() as conn:
                # Build query with optional date range
                if date_range_start and date_range_end:
                    rows = await conn.fetch(
                        f"""
                        SELECT id, session_id, description, reminder_date,
                               location, repeat_interval, created_at, notified
                        FROM {self._table_name}
                        WHERE session_id = $1
                          AND reminder_date BETWEEN $2 AND $3
                        ORDER BY reminder_date
                        """,
                        session_id,
                        date_range_start,
                        date_range_end
                    )
                elif date_range_start:
                    rows = await conn.fetch(
                        f"""
                        SELECT id, session_id, description, reminder_date,
                               location, repeat_interval, created_at, notified
                        FROM {self._table_name}
                        WHERE session_id = $1
                          AND reminder_date >= $2
                        ORDER BY reminder_date
                        """,
                        session_id,
                        date_range_start
                    )
                elif date_range_end:
                    rows = await conn.fetch(
                        f"""
                        SELECT id, session_id, description, reminder_date,
                               location, repeat_interval, created_at, notified
                        FROM {self._table_name}
                        WHERE session_id = $1
                          AND reminder_date <= $2
                        ORDER BY reminder_date
                        """,
                        session_id,
                        date_range_end
                    )
                else:
                    rows = await conn.fetch(
                        f"""
                        SELECT id, session_id, description, reminder_date,
                               location, repeat_interval, created_at, notified
                        FROM {self._table_name}
                        WHERE session_id = $1
                        ORDER BY reminder_date
                        """,
                        session_id
                    )
                
                # Build reminder entities
                reminders = []
                for row in rows:
                    reminder = Reminder(
                        id=row['id'],
                        session_id=row['session_id'],
                        description=row['description'],
                        reminder_date=row['reminder_date'],
                        location=row['location'],
                        repeat_interval=row['repeat_interval'],
                        created_at=row['created_at'],
                        notified=row['notified']
                    )
                    reminders.append(reminder)
                
                return reminders
                
        except Exception as e:
            logger.error(f"Error getting reminders for session {session_id}: {e}")
            raise
    
    async def save(self, reminder: Reminder) -> None:
        """Save new reminder"""
        try:
            async with self._db_pool.transaction() as conn:
                await conn.execute(
                    f"""
                    INSERT INTO {self._table_name}
                    (id, session_id, description, reminder_date, location,
                     repeat_interval, created_at, notified)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    reminder.id,
                    reminder.session_id,
                    reminder.description,
                    reminder.reminder_date,
                    reminder.location,
                    reminder.repeat_interval,
                    reminder.created_at,
                    reminder.notified
                )
                
                logger.debug(f"Saved reminder {reminder.id} for session {reminder.session_id}")
                
        except Exception as e:
            logger.error(f"Error saving reminder: {e}")
            raise
    
    async def update(self, reminder: Reminder) -> None:
        """Update existing reminder"""
        try:
            async with self._db_pool.transaction() as conn:
                result = await conn.execute(
                    f"""
                    UPDATE {self._table_name}
                    SET description = $2,
                        reminder_date = $3,
                        location = $4,
                        repeat_interval = $5,
                        notified = $6
                    WHERE id = $1
                    """,
                    reminder.id,
                    reminder.description,
                    reminder.reminder_date,
                    reminder.location,
                    reminder.repeat_interval,
                    reminder.notified
                )
                
                if result == "UPDATE 0":
                    logger.warning(f"Reminder {reminder.id} not found for update")
                else:
                    logger.debug(f"Updated reminder {reminder.id}")
                
        except Exception as e:
            logger.error(f"Error updating reminder: {e}")
            raise
    
    async def delete(self, reminder_id: UUID) -> None:
        """Delete reminder by ID"""
        try:
            async with self._db_pool.transaction() as conn:
                result = await conn.execute(
                    f"""
                    DELETE FROM {self._table_name}
                    WHERE id = $1
                    """,
                    reminder_id
                )
                
                if result == "DELETE 0":
                    logger.warning(f"Reminder {reminder_id} not found for deletion")
                else:
                    logger.debug(f"Deleted reminder {reminder_id}")
                
        except Exception as e:
            logger.error(f"Error deleting reminder: {e}")
            raise
    
    async def get_by_id(self, reminder_id: UUID) -> Optional[Reminder]:
        """Get reminder by ID"""
        try:
            async with self._db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"""
                    SELECT id, session_id, description, reminder_date,
                           location, repeat_interval, created_at, notified
                    FROM {self._table_name}
                    WHERE id = $1
                    """,
                    reminder_id
                )
                
                if not row:
                    return None
                
                return Reminder(
                    id=row['id'],
                    session_id=row['session_id'],
                    description=row['description'],
                    reminder_date=row['reminder_date'],
                    location=row['location'],
                    repeat_interval=row['repeat_interval'],
                    created_at=row['created_at'],
                    notified=row['notified']
                )
                
        except Exception as e:
            logger.error(f"Error getting reminder {reminder_id}: {e}")
            raise
    
    async def get_upcoming(
        self,
        session_id: UUID,
        within_minutes: int = 60
    ) -> List[Reminder]:
        """Get upcoming reminders within specified minutes"""
        try:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT id, session_id, description, reminder_date,
                           location, repeat_interval, created_at, notified
                    FROM {self._table_name}
                    WHERE session_id = $1
                      AND reminder_date BETWEEN NOW() AND NOW() + INTERVAL '$2 minutes'
                      AND notified = FALSE
                    ORDER BY reminder_date
                    """,
                    session_id,
                    within_minutes
                )
                
                reminders = []
                for row in rows:
                    reminder = Reminder(
                        id=row['id'],
                        session_id=row['session_id'],
                        description=row['description'],
                        reminder_date=row['reminder_date'],
                        location=row['location'],
                        repeat_interval=row['repeat_interval'],
                        created_at=row['created_at'],
                        notified=row['notified']
                    )
                    reminders.append(reminder)
                
                return reminders
                
        except Exception as e:
            logger.error(f"Error getting upcoming reminders: {e}")
            raise
    
    async def mark_as_notified(self, reminder_id: UUID) -> None:
        """Mark reminder as notified"""
        try:
            async with self._db_pool.transaction() as conn:
                result = await conn.execute(
                    f"""
                    UPDATE {self._table_name}
                    SET notified = TRUE
                    WHERE id = $1
                    """,
                    reminder_id
                )
                
                if result == "UPDATE 0":
                    logger.warning(f"Reminder {reminder_id} not found for marking as notified")
                else:
                    logger.debug(f"Marked reminder {reminder_id} as notified")
                
        except Exception as e:
            logger.error(f"Error marking reminder as notified: {e}")
            raise
    
    async def get_overdue(self, session_id: UUID) -> List[Reminder]:
        """Get overdue reminders that haven't been notified"""
        try:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT id, session_id, description, reminder_date,
                           location, repeat_interval, created_at, notified
                    FROM {self._table_name}
                    WHERE session_id = $1
                      AND reminder_date < NOW()
                      AND notified = FALSE
                    ORDER BY reminder_date
                    """,
                    session_id
                )
                
                reminders = []
                for row in rows:
                    reminder = Reminder(
                        id=row['id'],
                        session_id=row['session_id'],
                        description=row['description'],
                        reminder_date=row['reminder_date'],
                        location=row['location'],
                        repeat_interval=row['repeat_interval'],
                        created_at=row['created_at'],
                        notified=row['notified']
                    )
                    reminders.append(reminder)
                
                return reminders
                
        except Exception as e:
            logger.error(f"Error getting overdue reminders: {e}")
            raise
