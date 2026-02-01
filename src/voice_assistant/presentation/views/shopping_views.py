"""
Shopping list views for Gateway Service.
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import Request, HTTPException, Query

from .base import BaseViewSet, viewset
from ..schemas import (
    ShoppingItemCreateRequest,
    ShoppingItemResponse,
    ShoppingListResponse,
    ShoppingItemUpdateRequest,
    ShoppingItemDeleteResponse,
)
from voice_assistant.domain.entities.shopping_list import ShoppingListItem
from voice_assistant.domain.value_objects.priority import Priority

logger = logging.getLogger(__name__)


@viewset("shopping", "/shopping")
class ShoppingViewSet(BaseViewSet):
    """
    ViewSet for shopping list management endpoints.
    Handles CRUD operations for shopping list items.
    """
    
    tags = ["Shopping"]
    
    def _register_routes(self) -> None:
        """Register shopping list routes"""
        # Item CRUD
        self.router.add_api_route(
            "/{session_id}/items",
            self.get_items,
            methods=["GET"],
            response_model=ShoppingListResponse,
            summary="Get shopping list",
            description="Get all items in a session's shopping list",
        )
        
        self.router.add_api_route(
            "/{session_id}/items",
            self.add_item,
            methods=["POST"],
            response_model=ShoppingItemResponse,
            summary="Add item",
            description="Add a new item to the shopping list",
        )
        
        self.router.add_api_route(
            "/{session_id}/items/{item_id}",
            self.update_item,
            methods=["PUT"],
            response_model=ShoppingItemResponse,
            summary="Update item",
            description="Update an existing shopping list item",
        )
        
        self.router.add_api_route(
            "/{session_id}/items/{item_id}",
            self.delete_item,
            methods=["DELETE"],
            response_model=ShoppingItemDeleteResponse,
            summary="Delete item",
            description="Delete an item from the shopping list",
        )
        
        # Bulk operations
        self.router.add_api_route(
            "/{session_id}/items/clear",
            self.clear_list,
            methods=["POST"],
            response_model=ShoppingListResponse,
            summary="Clear list",
            description="Clear all items from the shopping list",
        )

    def _get_shopping_repository(self, request: Request):
        """Get shopping repository from dependencies"""
        repo = self.get_dependency("shopping_repository")
        if repo is None:
            # Try to get from app state
            repo = self.get_state_attr(request, "shopping_repository")
        return repo

    def _map_priority(self, priority_str: str) -> Priority:
        """Map string priority to Priority enum"""
        priority_map = {
            "low": Priority.LOW,
            "normal": Priority.NORMAL,
            "high": Priority.HIGH,
        }
        return priority_map.get(priority_str.lower(), Priority.NORMAL)

    def _item_to_response(self, item: ShoppingListItem) -> ShoppingItemResponse:
        """Convert ShoppingListItem to response schema"""
        return ShoppingItemResponse(
            id=str(item.id),
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            priority=item.priority.value if hasattr(item.priority, 'value') else str(item.priority),
            added_at=item.added_at,
            purchased=False  # Default, would be stored in DB in real implementation
        )

    async def get_items(
        self,
        session_id: str,
        request: Request,
        include_purchased: bool = Query(True, description="Include purchased items"),
        sort_by: str = Query("added_at", description="Sort field (added_at, priority, name)")
    ) -> ShoppingListResponse:
        """
        Get shopping list for a session.
        
        Args:
            session_id: Session ID
            request: FastAPI request object
            include_purchased: Whether to include purchased items
            sort_by: Field to sort by
            
        Returns:
            ShoppingListResponse with items
        """
        try:
            # Validate session ID
            session_uuid = UUID(session_id)
            
            # Get repository
            repository = self._get_shopping_repository(request)
            
            if repository:
                # Use repository if available
                items = await repository.get_by_session_id(session_uuid)
            else:
                # Fallback: return empty list (mock behavior)
                logger.warning(f"No shopping repository available, returning empty list for {session_id}")
                items = []
            
            # Convert to response
            item_responses = [self._item_to_response(item) for item in items]
            
            # Filter purchased if needed
            if not include_purchased:
                item_responses = [item for item in item_responses if not item.purchased]
            
            # Sort
            if sort_by == "priority":
                item_responses.sort(key=lambda x: x.priority, reverse=True)
            elif sort_by == "name":
                item_responses.sort(key=lambda x: x.name)
            else:  # added_at
                item_responses.sort(key=lambda x: x.added_at, reverse=True)
            
            pending_count = sum(1 for item in item_responses if not item.purchased)
            purchased_count = sum(1 for item in item_responses if item.purchased)
            
            return ShoppingListResponse(
                session_id=session_id,
                items=item_responses,
                total_count=len(item_responses),
                pending_count=pending_count,
                purchased_count=purchased_count
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting shopping list: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def add_item(
        self,
        session_id: str,
        request_data: ShoppingItemCreateRequest,
        request: Request
    ) -> ShoppingItemResponse:
        """
        Add item to shopping list.
        
        Args:
            session_id: Session ID
            request_data: Item creation request
            request: FastAPI request object
            
        Returns:
            ShoppingItemResponse with created item
        """
        try:
            # Validate session ID
            session_uuid = UUID(session_id)
            
            # Create domain entity
            item = ShoppingListItem.create(
                name=request_data.name,
                quantity=request_data.quantity,
                unit=request_data.unit,
                priority=self._map_priority(request_data.priority)
            )
            
            # Get repository
            repository = self._get_shopping_repository(request)
            
            if repository:
                # Save to repository
                await repository.add_item(session_uuid, item)
                logger.info(f"Added item {item.name} to session {session_id}")
            else:
                logger.warning(f"No shopping repository available, item not persisted: {item.name}")
            
            return self._item_to_response(item)
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error adding shopping item: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def update_item(
        self,
        session_id: str,
        item_id: str,
        request_data: ShoppingItemUpdateRequest,
        request: Request
    ) -> ShoppingItemResponse:
        """
        Update shopping list item.
        
        Args:
            session_id: Session ID
            item_id: Item ID
            request_data: Update request
            request: FastAPI request object
            
        Returns:
            ShoppingItemResponse with updated item
        """
        try:
            session_uuid = UUID(session_id)
            item_uuid = UUID(item_id)
            
            repository = self._get_shopping_repository(request)
            
            if not repository:
                raise self.handle_error("Shopping repository not available", status_code=503)
            
            # Get existing item
            item = await repository.get_item_by_id(session_uuid, item_uuid)
            if not item:
                raise self.handle_error("Item not found", status_code=404)
            
            # Update fields
            if request_data.name is not None:
                item.name = request_data.name
            if request_data.quantity is not None:
                item.quantity = request_data.quantity
            if request_data.unit is not None:
                item.unit = request_data.unit
            if request_data.priority is not None:
                item.priority = self._map_priority(request_data.priority)
            
            # Save updated item
            await repository.update_item(session_uuid, item)
            
            logger.info(f"Updated item {item_id} in session {session_id}")
            
            return self._item_to_response(item)
            
        except ValueError:
            raise self.handle_error("Invalid ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating shopping item: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def delete_item(
        self,
        session_id: str,
        item_id: str,
        request: Request
    ) -> ShoppingItemDeleteResponse:
        """
        Delete shopping list item.
        
        Args:
            session_id: Session ID
            item_id: Item ID
            request: FastAPI request object
            
        Returns:
            ShoppingItemDeleteResponse with result
        """
        try:
            session_uuid = UUID(session_id)
            item_uuid = UUID(item_id)
            
            repository = self._get_shopping_repository(request)
            
            if not repository:
                raise self.handle_error("Shopping repository not available", status_code=503)
            
            # Delete item
            success = await repository.delete_item(session_uuid, item_uuid)
            
            if not success:
                raise self.handle_error("Item not found or could not be deleted", status_code=404)
            
            logger.info(f"Deleted item {item_id} from session {session_id}")
            
            return ShoppingItemDeleteResponse(
                success=True,
                message="Item deleted successfully",
                deleted_item_id=item_id
            )
            
        except ValueError:
            raise self.handle_error("Invalid ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting shopping item: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def clear_list(
        self,
        session_id: str,
        request: Request,
        only_purchased: bool = Query(False, description="Clear only purchased items")
    ) -> ShoppingListResponse:
        """
        Clear shopping list.
        
        Args:
            session_id: Session ID
            request: FastAPI request object
            only_purchased: Whether to clear only purchased items
            
        Returns:
            ShoppingListResponse with updated list
        """
        try:
            session_uuid = UUID(session_id)
            
            repository = self._get_shopping_repository(request)
            
            if repository:
                if only_purchased:
                    await repository.clear_purchased_items(session_uuid)
                else:
                    await repository.clear_all_items(session_uuid)
                
                logger.info(f"Cleared shopping list for session {session_id} (only_purchased={only_purchased})")
            else:
                logger.warning(f"No shopping repository available for clearing list {session_id}")
            
            # Return empty list
            return ShoppingListResponse(
                session_id=session_id,
                items=[],
                total_count=0,
                pending_count=0,
                purchased_count=0
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error clearing shopping list: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)