"""
PostgreSQL implementation of shopping list repository.
Implements IShoppingRepository with asyncpg and proper locking.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""
import logging
from typing import Optional
from uuid import UUID
import asyncpg

from ...domain.repositories.shopping_repository import IShoppingRepository
from ...domain.entities.shopping_list import ShoppingList, ShoppingListItem
from ...domain.value_objects.priority import Priority
from .database_connection import DatabaseConnectionPool, UnitOfWork

logger = logging.getLogger(__name__)


class PostgresShoppingRepository(IShoppingRepository):
    """
    PostgreSQL implementation of shopping list repository.
    
    Implements repository pattern with:
    - Connection pooling via DatabaseConnectionPool
    - Optimistic locking for concurrent access
    - Transaction support via UnitOfWork
    """
    
    def __init__(self, db_pool: DatabaseConnectionPool):
        self._db_pool = db_pool
        self._table_name = "shopping_lists"
        self._items_table = "shopping_list_items"
    
    async def get_by_session(self, session_id: UUID) -> Optional[ShoppingList]:
        """
        Get shopping list by session ID with all items.
        Uses row-level locking for consistent reads.
        """
        try:
            async with self._db_pool.acquire() as conn:
                # Get shopping list with lock
                row = await conn.fetchrow(
                    f"""
                    SELECT session_id, version, created_at, updated_at
                    FROM {self._table_name}
                    WHERE session_id = $1
                    FOR SHARE
                    """,
                    session_id
                )
                
                if not row:
                    return None
                
                # Get all items for this shopping list
                item_rows = await conn.fetch(
                    f"""
                    SELECT id, name, quantity, unit, priority, added_at
                    FROM {self._items_table}
                    WHERE session_id = $1
                    ORDER BY added_at
                    """,
                    session_id
                )
                
                # Build shopping list entity
                items = []
                for item_row in item_rows:
                    item = ShoppingListItem(
                        id=item_row['id'],
                        name=item_row['name'],
                        quantity=item_row['quantity'],
                        unit=item_row['unit'],
                        priority=Priority(item_row['priority']),
                        added_at=item_row['added_at']
                    )
                    items.append(item)
                
                return ShoppingList(
                    session_id=session_id,
                    items=items
                )
                
        except Exception as e:
            logger.error(f"Error getting shopping list for session {session_id}: {e}")
            raise
    
    async def save(self, shopping_list: ShoppingList) -> None:
        """
        Save new shopping list with items.
        Uses transaction to ensure atomicity.
        """
        try:
            async with self._db_pool.transaction() as conn:
                # Insert shopping list
                await conn.execute(
                    f"""
                    INSERT INTO {self._table_name} (session_id, version, created_at, updated_at)
                    VALUES ($1, 1, NOW(), NOW())
                    ON CONFLICT (session_id) DO UPDATE SET
                        version = {self._table_name}.version + 1,
                        updated_at = NOW()
                    """,
                    shopping_list.session_id
                )
                
                # Insert items
                for item in shopping_list.items:
                    await conn.execute(
                        f"""
                        INSERT INTO {self._items_table} 
                        (id, session_id, name, quantity, unit, priority, added_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            quantity = EXCLUDED.quantity,
                            unit = EXCLUDED.unit,
                            priority = EXCLUDED.priority
                        """,
                        item.id,
                        shopping_list.session_id,
                        item.name,
                        item.quantity,
                        item.unit,
                        item.priority.value,
                        item.added_at
                    )
                
                logger.debug(f"Saved shopping list for session {shopping_list.session_id}")
                
        except Exception as e:
            logger.error(f"Error saving shopping list: {e}")
            raise
    
    async def update(self, shopping_list: ShoppingList) -> None:
        """
        Update existing shopping list with optimistic locking.
        Raises ConcurrentModificationError if version mismatch.
        """
        try:
            async with self._db_pool.transaction() as conn:
                # Update with version check (optimistic locking)
                result = await conn.execute(
                    f"""
                    UPDATE {self._table_name}
                    SET version = version + 1,
                        updated_at = NOW()
                    WHERE session_id = $1
                    RETURNING version
                    """,
                    shopping_list.session_id
                )
                
                if result == "UPDATE 0":
                    raise ConcurrentModificationError(
                        f"Shopping list {shopping_list.session_id} was modified concurrently"
                    )
                
                # Delete existing items
                await conn.execute(
                    f"""
                    DELETE FROM {self._items_table}
                    WHERE session_id = $1
                    """,
                    shopping_list.session_id
                )
                
                # Insert updated items
                for item in shopping_list.items:
                    await conn.execute(
                        f"""
                        INSERT INTO {self._items_table} 
                        (id, session_id, name, quantity, unit, priority, added_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        item.id,
                        shopping_list.session_id,
                        item.name,
                        item.quantity,
                        item.unit,
                        item.priority.value,
                        item.added_at
                    )
                
                logger.debug(f"Updated shopping list for session {shopping_list.session_id}")
                
        except Exception as e:
            logger.error(f"Error updating shopping list: {e}")
            raise
    
    async def delete(self, session_id: UUID) -> None:
        """Delete shopping list and all its items"""
        try:
            async with self._db_pool.transaction() as conn:
                # Delete items first (cascade could also be used)
                await conn.execute(
                    f"""
                    DELETE FROM {self._items_table}
                    WHERE session_id = $1
                    """,
                    session_id
                )
                
                # Delete shopping list
                result = await conn.execute(
                    f"""
                    DELETE FROM {self._table_name}
                    WHERE session_id = $1
                    """,
                    session_id
                )
                
                if result == "DELETE 0":
                    logger.warning(f"Shopping list for session {session_id} not found for deletion")
                else:
                    logger.debug(f"Deleted shopping list for session {session_id}")
                
        except Exception as e:
            logger.error(f"Error deleting shopping list: {e}")
            raise
    
    async def add_item(self, session_id: UUID, item: ShoppingListItem) -> None:
        """Add a single item to existing shopping list"""
        try:
            async with self._db_pool.transaction() as conn:
                # Ensure shopping list exists
                await conn.execute(
                    f"""
                    INSERT INTO {self._table_name} (session_id, version, created_at, updated_at)
                    VALUES ($1, 1, NOW(), NOW())
                    ON CONFLICT (session_id) DO UPDATE SET
                        updated_at = NOW()
                    """,
                    session_id
                )
                
                # Insert item
                await conn.execute(
                    f"""
                    INSERT INTO {self._items_table} 
                    (id, session_id, name, quantity, unit, priority, added_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        quantity = EXCLUDED.quantity,
                        unit = EXCLUDED.unit,
                        priority = EXCLUDED.priority
                    """,
                    item.id,
                    session_id,
                    item.name,
                    item.quantity,
                    item.unit,
                    item.priority.value,
                    item.added_at
                )
                
                logger.debug(f"Added item {item.id} to shopping list {session_id}")
                
        except Exception as e:
            logger.error(f"Error adding item to shopping list: {e}")
            raise
    
    async def remove_item(self, session_id: UUID, item_id: UUID) -> bool:
        """Remove a single item from shopping list"""
        try:
            async with self._db_pool.acquire() as conn:
                result = await conn.execute(
                    f"""
                    DELETE FROM {self._items_table}
                    WHERE id = $1 AND session_id = $2
                    """,
                    item_id,
                    session_id
                )
                
                if result == "DELETE 1":
                    logger.debug(f"Removed item {item_id} from shopping list {session_id}")
                    return True
                else:
                    logger.warning(f"Item {item_id} not found in shopping list {session_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error removing item from shopping list: {e}")
            raise


class ConcurrentModificationError(Exception):
    """Raised when optimistic locking detects concurrent modification"""
    pass
